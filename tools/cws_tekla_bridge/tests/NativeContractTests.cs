using System;
using System.Collections.Generic;
using Cws.TeklaBridge.Core;
using Cws.TeklaBridge.Native;
namespace Cws.TeklaBridge.Tests
{
    public static class NativeContractTests
    {
        public static void Run(TestSuite t)
        {
            t.Check("native.disconnected_is_real_blocked_state",()=> { var adapter=new DisconnectedAdapter(); t.True(!adapter.IsFixture); t.True(!adapter.Capabilities.Supports("read")); t.True(!adapter.Capabilities.Supports("save")); t.Throws<NativeOperationBlockedException>(()=>adapter.GetIdentity()); t.Throws<NativeOperationBlockedException>(()=>adapter.ReadParts()); t.Throws<NativeOperationBlockedException>(()=>adapter.ReopenAndReadback()); });
            t.Check("native.source_material_required_no_default",()=> { var p=Simple(); p.Material=null; t.Throws<NativeOperationBlockedException>(()=>NativeGuards.ValidateSimplePayload(p)); });
            t.Check("native.s275jr_to_s355jr_not_silent",()=> { var p=Simple(); p.Material="S355JR"; t.Throws<NativeOperationBlockedException>(()=>NativeGuards.ValidateSimplePayload(p)); });
            t.Check("native.s275jr_exact_catalog_retained",()=> { var p=Simple(); NativeGuards.ValidateSimplePayload(p); NativeGuards.ValidateCatalog(p,new Dictionary<string,List<string>>{{"profiles",new List<string>{"IPE200"}},{"materials",new List<string>{"S275JR"}}}); t.Equal("S275JR",p.Material); t.Equal("S275JR",p.MaterialRaw); });
            t.Check("native.catalogs_no_alias_or_prefix_guess",()=> { var p=Simple(); t.Throws<NativeOperationBlockedException>(()=>NativeGuards.ValidateCatalog(p,new Dictionary<string,List<string>>{{"profiles",new List<string>{"IPE"}},{"materials",new List<string>{"S355JR"}}})); });
            t.Check("native.ownership_requires_all_matching_provenance",()=> { var p=Simple(); p.Managed=true; t.True(!NativeGuards.IsOwned(p)); Own(p); t.True(NativeGuards.IsOwned(p)); p.Udas["CWS_SOURCE_REV"]="another"; t.True(!NativeGuards.IsOwned(p)); });
            t.Check("native.manual_downstream_mutation_blocked",()=> { var p=Simple(); Own(p); p.ManualDownstream=true; t.Throws<NativeOperationBlockedException>(()=>NativeGuards.Protect(p,Simple())); });
            t.Check("native.canonical_identity_cannot_reassign",()=> { var p=Simple(); Own(p); var desired=Simple(); desired.CanonicalId="other"; t.Throws<NativeOperationBlockedException>(()=>NativeGuards.Protect(p,desired)); });
            t.Check("native.unsupported_shapes_holes_no_silent_loss",()=> { var p=Simple(); p.Kind="SHAPE"; t.Throws<NativeOperationBlockedException>(()=>NativeGuards.ValidateSimplePayload(p)); p=Simple(); p.Udas.Remove("NATIVE_FEATURE_POLICY"); t.Throws<NativeOperationBlockedException>(()=>NativeGuards.ValidateSimplePayload(p)); });
            t.Check("native.invalid_geometry_rejected",()=> { var p=Simple(); p.Points[1].X=Double.NaN; t.Throws<NativeOperationBlockedException>(()=>NativeGuards.ValidateSimplePayload(p)); p=Simple(); p.Points[1]=new Vec3(0,0,0); t.Throws<NativeOperationBlockedException>(()=>NativeGuards.ValidateSimplePayload(p)); });
        }
        private static CanonicalPart Simple() => new CanonicalPart { CanonicalId="part-1",SourceId="source-1",SourceRevision="rev-1",PhysicalRole="PRIMARY",Kind="BEAM",Profile="IPE200",MaterialRaw="S275JR",Material="S275JR",Points=new List<Vec3>{new Vec3(0,0,0),new Vec3(1000,0,0)},Udas=new Dictionary<string,string>{{"NATIVE_FEATURE_POLICY","EXPLICIT_NO_MANUFACTURING_FEATURES"},{"NATIVE_GEOMETRY_POLICY","LINEAR_NO_CHAMFERS"}} };
        private static void Own(CanonicalPart p) { p.Managed=true; p.Udas["CWS_OWNER"]=NativeGuards.Owner;p.Udas["CWS_CANONICAL_ID"]=p.CanonicalId;p.Udas["CWS_SOURCE_ID"]=p.SourceId;p.Udas["CWS_SOURCE_REV"]=p.SourceRevision;p.Udas["CWS_PHYSICAL_ROLE"]=p.PhysicalRole;p.Udas["CWS_SCHEMA"]="1.0"; }
    }
}
