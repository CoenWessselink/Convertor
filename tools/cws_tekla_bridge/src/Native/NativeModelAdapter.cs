using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using Cws.TeklaBridge.Core;
using Tekla.Structures;
using Tekla.Structures.Catalogs;
using Tekla.Structures.Geometry3d;
using Tekla.Structures.Model;
using NativePart = Tekla.Structures.Model.Part;
using UiSelector = Tekla.Structures.Model.UI.ModelObjectSelector;

namespace Cws.TeklaBridge.Native
{
    // Genuine Tekla Open API adapter. No reflection-based substitute, fake DLL, or fixture in this class.
    // API implementation is not runtime evidence. Production manifest starts with no approved writes.
    public sealed class NativeModelAdapter : IModelAdapter, IPersistenceEvidenceVerifier
    {
        private readonly object _gate = new object();
        private readonly NativeAdapterOptions _options;
        private Model _model;
        private ModelHandler _handler;
        private ModelIdentity _savedCheckpoint;
        private string _lastPersistenceSnapshotHash;
        private string _actualVersion;
        private Dictionary<string,string> _assemblyHashes;
        public string AdapterName => "TEKLA_NATIVE_VERSION_BOUND";
        public bool IsFixture => false;
        public NativeModelAdapter(NativeAdapterOptions options)
        {
            if(options==null) throw new ArgumentNullException(nameof(options));
            _options = new NativeAdapterOptions { ExpectedTeklaVersion=options.ExpectedTeklaVersion,ExpectedAssemblySha256=options.ExpectedAssemblySha256==null?new Dictionary<string,string>():new Dictionary<string,string>(options.ExpectedAssemblySha256,StringComparer.Ordinal),Authority=options.Authority,RuntimeEvidence=options.RuntimeEvidence };
            if (Environment.OSVersion.Platform != PlatformID.Win32NT || !Environment.Is64BitProcess)
                NativeGuards.Block("WINDOWS_X64_REQUIRED", "Native Tekla IPC requires actual Windows x64 runtime.");
            if (String.IsNullOrWhiteSpace(_options.ExpectedTeklaVersion))
                NativeGuards.Block("TEKLA_VERSION_UNVERIFIED", "Configure exact observed installed version; developer NuGet reference is not runtime proof.");
            _model = new Model(); _handler = new ModelHandler();
            EnsureConnected();
            _assemblyHashes = ReadAssemblyHashes();
        }
        public static bool TryConnect(NativeAdapterOptions options,out NativeModelAdapter adapter,out string reason)
        {
            try { adapter = new NativeModelAdapter(options); reason = null; return true; }
            catch (Exception ex) { adapter = null; reason = ex.GetType().Name + ": " + ex.Message; return false; }
        }
        private void EnsureConnected()
        {
            if (!_model.GetConnectionStatus()) NativeGuards.Block("TEKLA_DISCONNECTED", "No live native model connection.");
            _actualVersion = TeklaStructuresInfo.GetCurrentProgramVersion();
            var api = typeof(Model).Assembly.GetName().Version;
            if (!String.Equals(_actualVersion,_options.ExpectedTeklaVersion,StringComparison.Ordinal) ||
                !String.Equals(_actualVersion.Split('.')[0],api.Major.ToString(CultureInfo.InvariantCulture),StringComparison.Ordinal))
                NativeGuards.Block("TEKLA_VERSION_MISMATCH", "Installed version differs from configured version or compiled API major.");
            var info = _model.GetInfo();
            if (String.IsNullOrWhiteSpace(info.ModelName) || String.IsNullOrWhiteSpace(info.ModelPath))
                NativeGuards.Block("MODEL_NOT_OPEN", "A real Tekla model must be open.");
        }
        public CapabilitySet Capabilities
        {
            get
            {
                var set = new CapabilitySet();
                foreach (var name in new[]{"read","model.identity","model.parts","model.read","catalogs","catalog.profiles","catalog.materials","catalog.components","catalog.shapes","selection.read","selection.set","selection.write","plan.create","plan.validate","geometry.read"}) set.Values[name] = true;
                foreach (var name in new[]{"upsert","part.upsert","plan.execute","transaction.write","persist.save","persist.reopen","beam.upsert","polybeam.upsert","plate.upsert","save","reopen","readback","remove","part.remove","shape.upsert","holes","bolts","welds","cuts","connections.apply","geometry.exact","manufacturing.readback"}) set.Values[name] = false;
                // Lifecycle/feature authority must match the frozen manifest and exact loaded assemblies.
                set.Values["save"] = RuntimeApproved("native.save");
                set.Values["reopen"] = RuntimeApproved("native.reopen");
                set.Values["readback"] = RuntimeApproved("native.readback") && set.Values["save"] && set.Values["reopen"];
                foreach (string kind in new[]{"beam","polybeam","plate"})
                    set.Values[kind+".upsert"] = RuntimeApproved("native."+kind+".upsert") && set.Values["readback"];
                set.Values["upsert"] = set.Values["beam.upsert"] && set.Values["polybeam.upsert"] && set.Values["plate.upsert"];
                set.Values["part.upsert"] = set.Values["upsert"];
                set.Values["persist.save"] = set.Values["save"]; set.Values["persist.reopen"] = set.Values["reopen"];
                set.Values["transaction.write"] = RuntimeApproved("native.transaction");
                set.Values["plan.execute"] = set.Values["part.upsert"] && set.Values["transaction.write"] && RuntimeApproved("native.write");
                return set;
            }
        }
        private bool RuntimeApproved(string component)
        {
            if (_options.Authority == null || _options.Authority.IsFixture || _options.RuntimeEvidence == null || _assemblyHashes == null || _options.ExpectedAssemblySha256 == null) return false;
            foreach (var pair in _assemblyHashes)
                if (!_options.ExpectedAssemblySha256.TryGetValue(pair.Key,out var expected) || !String.Equals(pair.Value,expected,StringComparison.OrdinalIgnoreCase)) return false;
            var record = _options.RuntimeEvidence(component);
            return _options.Authority.IsApproved(record,component);
        }
        private void RequireRuntime(string component)
        {
            EnsureConnected();
            if (!RuntimeApproved(component)) NativeGuards.Block("NATIVE_RUNTIME_UNPROVEN", "Frozen authority and matching version/assembly/runtime proof required for " + component + ".");
        }
        public ModelIdentity GetIdentity()
        {
            lock(_gate) { EnsureConnected(); return ReadIdentity(ReadParts()); }
        }
        private ModelIdentity ReadIdentity(List<CanonicalPart> parts)
        {
            var info = _model.GetInfo();
            var fullPath = Path.GetFullPath(info.ModelPath).TrimEnd(Path.DirectorySeparatorChar,Path.AltDirectorySeparatorChar);
            return new ModelIdentity
            {
                // Public ModelInfo has no model GUID. Expose truthful path/name binding, not a fabricated GUID.
                ModelId = "path:" + JsonUtil.Hash(new { Path = fullPath, info.ModelName }), ModelPath = fullPath,
                ModelName = info.ModelName, TeklaVersion = _actualVersion,
                Revision = JsonUtil.Hash(parts.OrderBy(p=>p.NativeId,StringComparer.Ordinal).Select(p=>new { p.NativeId,p.Kind,p.Profile,p.Material,p.Phase,p.Mark,p.Points,p.GeometryHash,p.Udas,p.ManualDownstream }).ToList())
            };
        }
        private T InGlobalPlane<T>(Func<T> action)
        {
            var handler = _model.GetWorkPlaneHandler();
            var previous = handler.GetCurrentTransformationPlane();
            if (previous == null) NativeGuards.Block("WORK_PLANE_UNREADABLE", "Cannot capture user work plane safely.");
            try
            {
                if (!handler.SetCurrentTransformationPlane(new TransformationPlane())) NativeGuards.Block("GLOBAL_PLANE_FAILED", "Failed to establish global XYZ coordinates.");
                return action();
            }
            finally
            {
                if (!handler.SetCurrentTransformationPlane(previous)) NativeGuards.Block("WORK_PLANE_RESTORE_FAILED", "User work plane restore failed; stop the run.");
            }
        }
        public List<CanonicalPart> ReadParts()
        {
            lock(_gate)
            {
                EnsureConnected();
                return InGlobalPlane(() =>
                {
                    var result = new List<CanonicalPart>();
                    var objects = _model.GetModelObjectSelector().GetAllObjects();
                    while(objects.MoveNext()) if (objects.Current is NativePart part) result.Add(ReadPart(part));
                    return result;
                });
            }
        }
        private CanonicalPart ReadPart(NativePart part)
        {
            string guid = _model.GetGUIDByIdentifier(part.Identifier);
            if (String.IsNullOrWhiteSpace(guid)) NativeGuards.Block("NATIVE_GUID_MISSING", "Numeric IDs are not persistent object identities.");
            var udas = new Dictionary<string,string>(StringComparer.Ordinal);
            foreach(var key in NativeGuards.OwnershipUdas) { string value = ""; if (part.GetUserProperty(key,ref value)) udas[key] = value; }
            var kind = part is Beam ? "BEAM" : part is PolyBeam ? "POLYBEAM" : part is ContourPlate ? "PLATE" : "UNSUPPORTED:" + part.GetType().Name;
            var points = new List<Vec3>();
            object geometryDetail = null;
            if (part is Beam beam)
            {
                points.Add(ToVec(beam.StartPoint)); points.Add(ToVec(beam.EndPoint));
                geometryDetail = new { StartOffset = OffsetValues(beam.StartPointOffset), EndOffset = OffsetValues(beam.EndPointOffset) };
            }
            else if (part is PolyBeam poly) { points = ContourPoints(poly.Contour); geometryDetail = ContourDetails(poly.Contour); }
            else if (part is ContourPlate plate) { points = ContourPoints(plate.Contour); geometryDetail = ContourDetails(plate.Contour); }
            string phaseValue = null; if (part.GetPhase(out Phase phase) && phase != null) phaseValue = phase.PhaseNumber.ToString(CultureInfo.InvariantCulture);
            string mark = part.GetPartMark();
            // Read IDs/counts only. Feature geometry/material/manufacturing are deliberately UNPROVEN.
            var features = new SortedSet<string>(StringComparer.Ordinal);
            AddRelated(features,"child",part.GetChildren()); AddRelated(features,"boolean",part.GetBooleans());
            AddRelated(features,"bolt",part.GetBolts()); AddRelated(features,"weld",part.GetWelds()); AddRelated(features,"component",part.GetComponents());
            var father = part.GetFatherComponent(); if (father != null) features.Add("father:"+_model.GetGUIDByIdentifier(father.Identifier));
            var assembly = part.GetAssembly();
            if (assembly != null)
            {
                var main = assembly.GetMainPart();
                if (main != null && main.Identifier.ID != part.Identifier.ID) features.Add("assembly-main:"+_model.GetGUIDByIdentifier(main.Identifier));
                foreach(ModelObject secondary in assembly.GetSecondaries()) features.Add("assembly-secondary:"+_model.GetGUIDByIdentifier(secondary.Identifier));
            }
            object solidObservation = null;
            try { var solid = part.GetSolid(); if (solid != null && solid.IsValid()) solidObservation = new { Min=ToVec(solid.MinimumPoint),Max=ToVec(solid.MaximumPoint) }; }
            catch(Exception ex) { udas["READBACK_SOLID_ERROR"] = ex.GetType().Name; }
            udas["READBACK_NATIVE_PROPERTIES"] = JsonUtil.Serialize(new { part.Name,part.Class,PartNumber=new {part.PartNumber.Prefix,part.PartNumber.StartNumber},AssemblyNumber=new {part.AssemblyNumber.Prefix,part.AssemblyNumber.StartNumber} });
            udas["READBACK_GEOMETRY_STATUS"] = "OBSERVED_POINTS_PLACEMENT_BBOX_NOT_EXACT_BREP";
            udas["READBACK_MANUFACTURING_STATUS"] = "UNPROVEN_FEATURE_GEOMETRY";
            udas["READBACK_RELATED_IDS"] = String.Join("|",features);
            var actual = new CanonicalPart
            {
                CanonicalId = Value(udas,"CWS_CANONICAL_ID") ?? "native:" + guid, SourceId = Value(udas,"CWS_SOURCE_ID"),
                SourceRevision = Value(udas,"CWS_SOURCE_REV"), PhysicalRole = Value(udas,"CWS_PHYSICAL_ROLE") ?? "UNMANAGED",
                Kind=kind,Profile=part.Profile.ProfileString,MaterialRaw=part.Material.MaterialString,Material=part.Material.MaterialString,
                Points=points,Phase=phaseValue,Mark=mark,Udas=udas,NativeId=guid,ManualDownstream=features.Count>0,
                ManufacturingHash=null
            };
            actual.Managed = NativeGuards.Exact(udas,"CWS_OWNER",NativeGuards.Owner) && NativeGuards.Exact(udas,"CWS_SCHEMA","1.0") &&
                !String.IsNullOrWhiteSpace(actual.SourceId) && !String.IsNullOrWhiteSpace(actual.SourceRevision) &&
                NativeGuards.Exact(udas,"CWS_CANONICAL_ID",actual.CanonicalId) && NativeGuards.Exact(udas,"CWS_PHYSICAL_ROLE",actual.PhysicalRole);
            actual.GeometryHash = points.Count == 0 ? null : JsonUtil.Hash(new { Schema="NATIVE_OBSERVATION_V1",kind,points,geometryDetail,
                actual.Profile,actual.Material,Position = PositionValues(part.Position),solidObservation });
            return actual;
        }
        private void AddRelated(SortedSet<string> values,string prefix,ModelObjectEnumerator e)
        {
            if(e==null) NativeGuards.Block("RELATED_OBJECT_READ_FAILED", "Related objects unreadable; downstream protection cannot be proven.");
            while(e.MoveNext()) if(e.Current!=null) values.Add(prefix+":"+_model.GetGUIDByIdentifier(e.Current.Identifier));
        }
        public List<string> GetSelection()
        {
            lock(_gate) { EnsureConnected(); var result=new List<string>(); var e=new UiSelector().GetSelectedObjects(); while(e.MoveNext()) result.Add(_model.GetGUIDByIdentifier(e.Current.Identifier)); return result; }
        }
        public void SetSelection(List<string> ids)
        {
            lock(_gate)
            {
                EnsureConnected(); if(ids==null) throw new ArgumentNullException(nameof(ids)); var selected=new ArrayList();
                foreach(string guid in ids.Distinct(StringComparer.Ordinal)) { var id=_model.GetIdentifierByGUID(guid); var obj=id==null?null:_model.SelectModelObject(id); if(obj==null) NativeGuards.Block("SELECTION_OBJECT_MISSING","Native GUID not found: "+guid); selected.Add(obj); }
                if(!new UiSelector().Select(selected)) NativeGuards.Block("SELECTION_FAILED","Tekla rejected selection change.");
            }
        }
        public Dictionary<string,List<string>> ReadCatalogs()
        {
            lock(_gate)
            {
                EnsureConnected(); var catalogs=new CatalogHandler(); if(!catalogs.GetConnectionStatus()) NativeGuards.Block("CATALOG_DISCONNECTED","Real catalog connection required.");
                var result=new Dictionary<string,List<string>>(StringComparer.Ordinal) { ["profiles"]=new List<string>(),["materials"]=new List<string>(),["components"]=new List<string>(),["shapes"]=new List<string>(),["parametricProfilePrefixes"]=new List<string>() };
                var profiles=catalogs.GetLibraryProfileItems(); while(profiles.MoveNext()) if(profiles.Current is LibraryProfileItem p) result["profiles"].Add(p.ProfileName);
                var parametric=catalogs.GetParametricProfileItems(); while(parametric.MoveNext()) if(parametric.Current is ParametricProfileItem p) result["parametricProfilePrefixes"].Add(p.ProfilePrefix);
                var materials=catalogs.GetMaterialItems(); while(materials.MoveNext()) if(materials.Current is MaterialItem m) result["materials"].Add(m.MaterialName);
                var components=catalogs.GetComponentItems(); while(components.MoveNext()) if(components.Current is ComponentItem c) result["components"].Add(c.Number.ToString(CultureInfo.InvariantCulture)+":"+c.Name);
                var shapes=catalogs.GetShapeItems(); while(shapes.MoveNext()) if(shapes.Current is ShapeItem s) result["shapes"].Add(s.Name);
                foreach(var key in result.Keys.ToList()) result[key]=result[key].Distinct(StringComparer.Ordinal).OrderBy(x=>x,StringComparer.Ordinal).ToList();
                return result;
            }
        }
        public void Upsert(CanonicalPart desired)
        {
            lock(_gate)
            {
                _lastPersistenceSnapshotHash=null;
                NativeGuards.ValidateSimplePayload(desired);
                string component="native."+desired.Kind.ToLowerInvariant()+".upsert";
                RequireRuntime(component); RequireRuntime("native.readback"); RequireRuntime("native.save"); RequireRuntime("native.reopen");
                if(!_options.Authority.IsApproved(desired.GeometryAuthority,"source.geometry") || !_options.Authority.IsApproved(desired.ProfileAuthority,"source.profile") || !_options.Authority.IsApproved(desired.MaterialAuthority,"source.material"))
                    NativeGuards.Block("SOURCE_AUTHORITY_UNPROVEN","Geometry, profile and material source authority must match frozen evidence.");
                NativeGuards.ValidateCatalog(desired,ReadCatalogs());
                if(desired.Udas.Keys.Any(k=>!NativeFieldKeys.Contains(k,StringComparer.Ordinal) && !NativeGuards.OwnershipUdas.Contains(k,StringComparer.Ordinal))) NativeGuards.Block("UDA_NOT_ALLOWLISTED","Unknown UDA write requested.");
                // Parse all placement/class/numbering fields before any insert/modify.
                var placement=ReadExplicitPosition(desired);
                string name=Required(desired,"NATIVE_NAME"),classValue=Required(desired,"NATIVE_CLASS");
                var partNumber=new NumberingSeries(Required(desired,"NATIVE_PART_PREFIX"),RequiredInt(desired,"NATIVE_PART_START"));
                var assemblyNumber=new NumberingSeries(Required(desired,"NATIVE_ASSEMBLY_PREFIX"),RequiredInt(desired,"NATIVE_ASSEMBLY_START"));
                if(!Int32.TryParse(desired.Phase,NumberStyles.Integer,CultureInfo.InvariantCulture,out int phaseNo) || phaseNo<1) NativeGuards.Block("PHASE_REQUIRED","Explicit existing numeric phase required.");
                var phase=new Phase(phaseNo); if(!phase.Select()) NativeGuards.Block("PHASE_NOT_FOUND","No implicit phase creation.");
                InGlobalPlane(() =>
                {
                    var matches=ReadParts().Where(x=>x.Key==desired.Key).ToList();
                    if(matches.Count>1) NativeGuards.Block("DUPLICATE_CANONICAL_ROLE","Multiple native parts use one canonical role.");
                    NativePart native=null; bool insert=matches.Count==0;
                    if(!insert)
                    {
                        var actual=matches[0]; NativeGuards.Protect(actual,desired);
                        if(!String.IsNullOrWhiteSpace(desired.NativeId) && !String.Equals(desired.NativeId,actual.NativeId,StringComparison.Ordinal)) NativeGuards.Block("NATIVE_ID_MISMATCH","Native GUID differs from existing canonical role.");
                        if(actual.Kind!=desired.Kind) NativeGuards.Block("KIND_CHANGE_BLOCKED","Native type replacement is not implemented.");
                        native=_model.SelectModelObject(_model.GetIdentifierByGUID(actual.NativeId)) as NativePart;
                    }
                    else if(!String.IsNullOrWhiteSpace(desired.NativeId)) NativeGuards.Block("STALE_NATIVE_ID","CREATE with a preexisting native GUID is blocked.");
                    if(native==null && !insert) NativeGuards.Block("NATIVE_OBJECT_MISSING","Part changed before write.");
                    if(desired.Kind=="BEAM")
                    {
                        var beam= native as Beam ?? new Beam(); beam.StartPoint=ToPoint(desired.Points[0]); beam.EndPoint=ToPoint(desired.Points[1]);
                        beam.StartPointOffset=ReadExplicitOffset(desired,"NATIVE_START_OFFSET_"); beam.EndPointOffset=ReadExplicitOffset(desired,"NATIVE_END_OFFSET_"); native=beam;
                    }
                    else
                    {
                        var contour=new Contour(); foreach(var point in desired.Points) contour.AddContourPoint(new ContourPoint(ToPoint(point),new Chamfer(0,0,Chamfer.ChamferTypeEnum.CHAMFER_NONE)));
                        if(desired.Kind=="POLYBEAM") { var poly=native as PolyBeam ?? new PolyBeam(); poly.Contour=contour; native=poly; }
                        else { var plate=native as ContourPlate ?? new ContourPlate(); plate.Contour=contour; native=plate; }
                    }
                    native.Profile.ProfileString=desired.Profile; native.Material.MaterialString=desired.Material;
                    native.Position=placement; native.Name=name; native.Class=classValue; native.PartNumber=partNumber; native.AssemblyNumber=assemblyNumber;
                    if(!native.SetPhase(phase)) NativeGuards.Block("NATIVE_PHASE_REJECTED","Phase was not applied.");
                    if(!(insert?native.Insert():native.Modify())) NativeGuards.Block("NATIVE_UPSERT_FAILED","Tekla Insert/Modify returned false.");
                    // Unknown ownership UDA definitions return false and stop the run. A partial insert is journaled by the engine; no guessed delete rollback.
                    var ownership=new Dictionary<string,string> { ["CWS_OWNER"]=NativeGuards.Owner,["CWS_CANONICAL_ID"]=desired.CanonicalId,["CWS_SOURCE_ID"]=desired.SourceId,["CWS_SOURCE_REV"]=desired.SourceRevision,["CWS_PHYSICAL_ROLE"]=desired.PhysicalRole,["CWS_SCHEMA"]="1.0" };
                    foreach(var pair in ownership) if(!native.SetUserProperty(pair.Key,pair.Value)) NativeGuards.Block("NATIVE_UDA_REJECTED","Configure and validate UDA definition: "+pair.Key);
                    if(!_model.CommitChanges("CWS bridge native upsert; persistence still requires Save/Reopen/Readback")) NativeGuards.Block("NATIVE_COMMIT_FAILED","CommitChanges failed; it is not Save proof.");
                    return true;
                });
                _savedCheckpoint=null;
            }
        }
        public void Remove(CanonicalPart part) => NativeGuards.Block("REMOVE_NOT_IMPLEMENTED","No native delete: ownership, journal, source removal and downstream proof require dedicated validated implementation.");
        public void Save()
        {
            lock(_gate)
            {
                _lastPersistenceSnapshotHash=null;
                RequireRuntime("native.save"); var before=GetIdentity();
                if(!_handler.Save("CWS bridge persistent checkpoint","CWS","CWS_SAVE_REOPEN_READBACK")) NativeGuards.Block("NATIVE_SAVE_FAILED","ModelHandler.Save returned false.");
                if(!_handler.IsModelSaved() || !before.ExactlyEquals(GetIdentity())) NativeGuards.Block("NATIVE_SAVE_UNSTABLE","Saved-state or identity changed during persistence.");
                _savedCheckpoint=before;
            }
        }
        public AdapterSnapshot ReopenAndReadback()
        {
            lock(_gate)
            {
                _lastPersistenceSnapshotHash=null;
                RequireRuntime("native.reopen"); RequireRuntime("native.readback");
                if(_savedCheckpoint==null || !_handler.IsModelSaved() || !_savedCheckpoint.ExactlyEquals(GetIdentity())) NativeGuards.Block("REOPEN_CHECKPOINT_REQUIRED","Native saved checkpoint must exactly match the current unchanged model.");
                var checkpoint=_savedCheckpoint; var started=DateTime.UtcNow;
                _handler.Close();
                var closed=new Model(); var closedInfo=closed.GetInfo();
                if(!String.IsNullOrWhiteSpace(closedInfo.ModelName)) NativeGuards.Block("REOPEN_CLOSE_UNPROVEN","Actual model close was not observed.");
                if(!_handler.Open(checkpoint.ModelPath,false)) NativeGuards.Block("NATIVE_REOPEN_FAILED","ModelHandler.Open returned false; autosave explicitly excluded.");
                _model=new Model(); EnsureConnected(); var parts=ReadParts(); var identity=ReadIdentity(parts);
                if(!checkpoint.ExactlyEquals(identity)) NativeGuards.Block("PERSISTENCE_DELTA","Independent native identity/state differs after genuine Close/Open.");
                _savedCheckpoint=null;
                var snapshot = new AdapterSnapshot { Identity=identity,Parts=parts,IsFixture=false,
                    PersistenceProof=JsonUtil.Serialize(new{Kind="NATIVE_MODELHANDLER_SAVE_CLOSE_OPEN_READBACK",Nonce=Guid.NewGuid().ToString("N"),StartedUtc=started,CompletedUtc=DateTime.UtcNow,Model=identity.Key,identity.Revision,ActualTeklaVersion=_actualVersion,AssemblySha256=_assemblyHashes,RuntimeAuthority="FROZEN_MANIFEST_VALIDATED",ManufacturingEvidence="UNPROVEN"}) };
                _lastPersistenceSnapshotHash=JsonUtil.Hash(snapshot);
                return snapshot;
            }
        }
        public bool VerifyPersistenceEvidence(AdapterSnapshot snapshot)
        {
            lock(_gate)
            {
                if(snapshot==null || snapshot.IsFixture || _lastPersistenceSnapshotHash==null) return false;
                try
                {
                    if(!RuntimeApproved("native.save") || !RuntimeApproved("native.reopen") || !RuntimeApproved("native.readback") ||
                        !String.Equals(_lastPersistenceSnapshotHash,JsonUtil.Hash(snapshot),StringComparison.Ordinal) ||
                        snapshot.Identity==null || !snapshot.Identity.ExactlyEquals(GetIdentity())) return false;
                    _lastPersistenceSnapshotHash=null; // One execution may consume one genuine lifecycle proof.
                    return true;
                }
                catch(Exception) { _lastPersistenceSnapshotHash=null; return false; }
            }
        }
        public NativeDiagnostics GetDiagnostics()
        {
            lock(_gate)
            {
                EnsureConnected(); var capabilities=Capabilities;
                return new NativeDiagnostics { AdapterName=AdapterName,ActualTeklaVersion=_actualVersion,ActualTeklaBuild=TeklaStructuresInfo.GetBuildNumber().ToString(),ReferenceApiVersion=typeof(Model).Assembly.GetName().Version.ToString(),IdentityMethod="ModelInfo path/name binding + independent part-state revision (not a model GUID)",AssemblySha256=new Dictionary<string,string>(_assemblyHashes),
                    Capabilities=capabilities.Values.Select(x=>new NativeCapabilityDetail{Name=x.Key,Implemented=!new[]{"remove","shape.upsert","holes","bolts","welds","cuts","connections.apply","geometry.exact","manufacturing.readback"}.Contains(x.Key),Enabled=x.Value,RuntimeProven=x.Value && !new[]{"read","model.identity","model.parts","model.read","catalogs","catalog.profiles","catalog.materials","catalog.components","catalog.shapes","selection.read","selection.set","selection.write","plan.create","plan.validate","geometry.read"}.Contains(x.Key),Reason=x.Value?"Live read/UI selection API available; exact manufacturing proof separately blocked.":"Unavailable or no frozen runtime evidence; no production authority."}).ToList(),
                    Sources=new List<string>{"https://api.nuget.org/v3-flatcontainer/tekla.structures.model/2024.0.0/tekla.structures.model.2024.0.0.nupkg","https://developer.tekla.com/documentation/coordinate-systems-and-work-planes","https://developer.tekla.com/doc/tekla-structures/2025/save-method-string-string-52977","https://developer.tekla.com/doc/tekla-structures/2026/open-method-71972"} };
            }
        }
        private static Dictionary<string,string> ReadAssemblyHashes()
        {
            var result=new Dictionary<string,string>(StringComparer.Ordinal);
            foreach(var assembly in new[]{typeof(Model).Assembly,typeof(CatalogHandler).Assembly,typeof(TeklaStructuresInfo).Assembly})
            {
                using(var stream=File.OpenRead(assembly.Location)) using(var sha=SHA256.Create()) result[assembly.GetName().Name]=BitConverter.ToString(sha.ComputeHash(stream)).Replace("-","").ToLowerInvariant();
            }
            return result;
        }
        private static readonly string[] NativeFieldKeys = { "NATIVE_NAME","NATIVE_CLASS","NATIVE_PART_PREFIX","NATIVE_PART_START","NATIVE_ASSEMBLY_PREFIX","NATIVE_ASSEMBLY_START",
            "NATIVE_POSITION_PLANE","NATIVE_POSITION_DEPTH","NATIVE_POSITION_ROTATION","NATIVE_PLANE_OFFSET","NATIVE_DEPTH_OFFSET","NATIVE_ROTATION_OFFSET",
            "NATIVE_START_OFFSET_X","NATIVE_START_OFFSET_Y","NATIVE_START_OFFSET_Z","NATIVE_END_OFFSET_X","NATIVE_END_OFFSET_Y","NATIVE_END_OFFSET_Z",
            "NATIVE_FEATURE_POLICY","NATIVE_GEOMETRY_POLICY" };
        private static string Value(Dictionary<string,string> values,string key) => values.TryGetValue(key,out var value)?value:null;
        private static Vec3 ToVec(Point point) => new Vec3(point.X,point.Y,point.Z);
        private static Point ToPoint(Vec3 point) => new Point(point.X,point.Y,point.Z);
        private static List<Vec3> ContourPoints(Contour contour) => contour.ContourPoints.Cast<ContourPoint>().Select(ToVec).ToList();
        private static object ContourDetails(Contour contour) => contour.ContourPoints.Cast<ContourPoint>().Select(p=>new{Point=ToVec(p),Chamfer=p.Chamfer==null?null:new{Type=p.Chamfer.Type.ToString(),p.Chamfer.X,p.Chamfer.Y,p.Chamfer.DZ1,p.Chamfer.DZ2}}).ToList();
        private static object OffsetValues(Offset p) => new{p.Dx,p.Dy,p.Dz};
        private static object PositionValues(Position p) => new{Plane=p.Plane.ToString(),Depth=p.Depth.ToString(),Rotation=p.Rotation.ToString(),p.PlaneOffset,p.DepthOffset,p.RotationOffset};
        private static string Required(CanonicalPart p,string key) { if(!p.Udas.TryGetValue(key,out var value) || value==null) NativeGuards.Block("NATIVE_FIELD_REQUIRED","Explicit field required: "+key); return value; }
        private static int RequiredInt(CanonicalPart p,string key) { if(!Int32.TryParse(Required(p,key),NumberStyles.Integer,CultureInfo.InvariantCulture,out int value) || value<0) NativeGuards.Block("NATIVE_FIELD_INVALID",key); return value; }
        private static double RequiredDouble(CanonicalPart p,string key) { if(!Double.TryParse(Required(p,key),NumberStyles.Float,CultureInfo.InvariantCulture,out double value) || !NativeGuards.Finite(value)) NativeGuards.Block("NATIVE_FIELD_INVALID",key); return value; }
        private static T RequiredEnum<T>(CanonicalPart p,string key) where T:struct { if(!Enum.TryParse(Required(p,key),false,out T value) || !Enum.IsDefined(typeof(T),value)) NativeGuards.Block("NATIVE_FIELD_INVALID",key); return value; }
        private static Offset ReadExplicitOffset(CanonicalPart p,string prefix) => new Offset { Dx=RequiredDouble(p,prefix+"X"),Dy=RequiredDouble(p,prefix+"Y"),Dz=RequiredDouble(p,prefix+"Z") };
        private static Position ReadExplicitPosition(CanonicalPart p) => new Position { Plane=RequiredEnum<Position.PlaneEnum>(p,"NATIVE_POSITION_PLANE"),Depth=RequiredEnum<Position.DepthEnum>(p,"NATIVE_POSITION_DEPTH"),Rotation=RequiredEnum<Position.RotationEnum>(p,"NATIVE_POSITION_ROTATION"),PlaneOffset=RequiredDouble(p,"NATIVE_PLANE_OFFSET"),DepthOffset=RequiredDouble(p,"NATIVE_DEPTH_OFFSET"),RotationOffset=RequiredDouble(p,"NATIVE_ROTATION_OFFSET") };
    }
}
