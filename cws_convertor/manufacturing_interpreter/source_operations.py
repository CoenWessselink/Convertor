"""Original NC1 operations can corroborate geometry; profile hints alone cannot."""
from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
import tempfile


def inspect_embedded_nc1(path: Path, source_shape, policy) -> dict | None:
    from canonical_model import extract_part_from_step, canonical_from_nc1_part
    from converter import parse_nc1
    from conversion import build_shape
    from .reconstruction import prove_equivalence
    from .contracts import GeometryProofStatus
    payload=extract_part_from_step(path,strict=True)
    if payload is None or 'nc1' not in payload.attachments:
        return None
    raw=payload.attachments['nc1'].bytes()
    with tempfile.TemporaryDirectory(prefix='cws-nc1-proof-') as folder:
        source=Path(folder)/'source.nc1';source.write_bytes(raw)
        parsed=parse_nc1(source)
        original=canonical_from_nc1_part(parsed)
        header_fields=('profile','profile_type','material','quantity','length','dim1','dim2','dim3','dim4','radius')
        agrees=all(getattr(original.header,k)==getattr(payload.header,k) for k in header_fields)
        agrees=agrees and asdict(original)['holes']==asdict(payload)['holes'] and asdict(original)['contours']==asdict(payload)['contours']
        if not agrees:
            return {'status':'CONFLICT','reason':'Payload disagrees with its original NC1 attachment'}
        rebuilt=build_shape(parsed).val()
        proof=prove_equivalence(source_shape,rebuilt,policy)
        proven=proof.status in {GeometryProofStatus.PROVEN_BREP_EQUIVALENT,GeometryProofStatus.PROVEN_WITHIN_POLICY}
        return {'status':'PROVEN' if proven else 'CONFLICT','header':asdict(original.header),
                'holes':[asdict(h) for h in original.holes], 'contours':[asdict(c) for c in original.contours],
                'original_nc1_sha256':payload.attachments['nc1'].sha256,
                'geometry_proof':asdict(proof), 'scope':'source-parametric profile, not a nominal catalogue certification'}


def compare_source_holes(header, expected, features, tolerance_mm=0.05):
    """One-to-one diameter/axis/entry-wall/position matching in the NC1 frame."""
    import math
    remaining=[(f.feature_id,dict(f.parameters)) for f in features if f.semantic_type.value=='HOLE']
    matches=[];problems=[]
    kind=header['profile_type'];h=header['dim1'];b=header['dim2'];tf=header['dim3'];tw=header['dim4']
    for number,hole in enumerate(expected):
        if hole.get('operation') or hole.get('depth',0):
            problems.append('SPECIAL_SOURCE_BORE_REQUIRES_DETAILED_MATCH');continue
        face=hole['face'];x=hole['x'];q=hole['q']
        if kind=='B':axis=(0,0,1);origin=(x,q,0);depth=header['dim2']
        elif kind in {'L','I','M'} and face in {'v','h'}:
            axis=(0,1,0);depth=min(tf,tw) if kind=='M' else tw
            y=(b-depth if face=='h' else 0) if kind=='M' else ((b-tw)/2 if kind=='I' else 0)
            origin=(x,y,q)
        elif kind in {'L','I','M'} and face in {'o','u'}:
            axis=(0,0,1);depth=min(tf,tw) if kind=='M' else tf
            z=h-depth if face=='o' and kind in {'I','M'} else 0
            origin=(x,q,z)
        else:
            problems.append('SOURCE_BORE_FRAME_NOT_SUPPORTED');continue
        candidates=[]
        for feature_id,params in remaining:
            direction=tuple(params.get('axis_'+c,0) for c in 'xyz')
            point=tuple(params.get('origin_'+c,0) for c in 'xyz')
            actual_depth=params.get('depth_mm',0)
            if sum(a*d for a,d in zip(axis,direction))<0:
                point=tuple(point[i]+direction[i]*actual_depth for i in range(3))
            distance=math.sqrt(sum((point[i]-origin[i])**2 for i in range(3)))
            if (abs(abs(sum(a*d for a,d in zip(axis,direction)))-1)<1e-6 and distance<=tolerance_mm
                    and abs(params.get('diameter_mm',2*params.get('radius_mm',0))-hole['diameter'])<=tolerance_mm
                    and abs(actual_depth-depth)<=tolerance_mm):candidates.append(feature_id)
        if len(candidates)!=1:problems.append('SOURCE_BORE_NOT_UNIQUELY_MATCHED:'+str(number))
        else:
            selected=candidates[0];remaining=[row for row in remaining if row[0]!=selected]
            matches.append({'source_index':number,'feature_id':selected,'face':face,'x':x,'q':q,'diameter':hole['diameter']})
    if remaining:problems.append('UNEXPECTED_GEOMETRIC_BORE')
    return {'status':'PASS' if not problems else 'FAIL','matches':matches,'problems':problems,
            'expected':len(expected),'matched':len(matches)}


def apply_source_profile(report, inspection):
    from dataclasses import replace
    from .contracts import GeometryProofStatus, ProfileRecognition, InterpretationReadiness
    evidence=(getattr(inspection, 'evidence', None) or {}).get('original_nc1_operations')
    if not evidence:
        return report
    if evidence.get('status') != 'PROVEN':
        return replace(report, readiness=InterpretationReadiness.BLOCKED,
                       blockers=tuple(dict.fromkeys((*report.blockers, "ORIGINAL_NC1_EVIDENCE_CONFLICT"))),
                       representability=tuple((target, "BLOCKED") for target, _ in report.representability))
    # Full original feature list and its source-frame coordinates remain the
    # authority; geometric hypotheses must not erase an explicit operation.
    header=evidence['header']
    geometry_proven=report.equivalence.status in {GeometryProofStatus.PROVEN_BREP_EQUIVALENT,GeometryProofStatus.PROVEN_WITHIN_POLICY}
    if not geometry_proven:return report
    profile=report.profile
    if profile.status!=GeometryProofStatus.PROVEN_WITHIN_POLICY:
        profile=ProfileRecognition(status=GeometryProofStatus.PROVEN_WITHIN_POLICY,
             designation=header['profile'],profile_type=header['profile_type'],family=header['profile_type'],
             confidence=1.0,candidates=(header['profile'],),
             reason='Bronparameters en onafhankelijk herbouwde NC1-geometrie komen overeen; geen nominale catalogusradius opgelegd.')
    blockers=[b for b in report.blockers if b!='CATALOG_PROFILE_NOT_PROVEN']
    recognised=sum(f.semantic_type.value in {'HOLE','COUNTERSINK','COUNTERBORE'} for f in report.features)
    hole_match=compare_source_holes(header,evidence['holes'],report.features)
    if hole_match['status']!='PASS':blockers.append('SOURCE_OPERATION_COMPLETENESS_NOT_PROVEN')
    return replace(report,profile=profile,blockers=tuple(dict.fromkeys(blockers)),
             readiness=InterpretationReadiness.BLOCKED if hole_match['status']!='PASS' else report.readiness,
             representability=tuple((target, "BLOCKED") for target, _ in report.representability) if hole_match['status']!='PASS' else report.representability,
             evidence=(*report.evidence,
             ('profile_evidence','original-NC1-parameters-with-local-BREP-proof'),
             ('source_hole_count',str(len(evidence['holes']))),('recognised_hole_count',str(recognised)),
             ('source_hole_frame_match',__import__('json').dumps(hole_match,sort_keys=True))))


def apply_custom_section(report, shape, policy):
    """Name an exact source-supported custom section without inventing a grade."""
    from dataclasses import replace
    from .contracts import GeometryProofStatus, ProfileRecognition, stable_id
    proven={GeometryProofStatus.PROVEN_BREP_EQUIVALENT,GeometryProofStatus.PROVEN_WITHIN_POLICY}
    if report.profile.status in proven or report.equivalence.status not in proven or report.section is None:
        return report
    # No catalogue match is not a reason to discard a proven custom cross-section.
    # Existing residual, material, target and axis blockers remain in force.
    designation='CUSTOM-'+stable_id('section',asdict(report.section)).split(':')[-1][:12]
    profile=ProfileRecognition(status=report.profile.status,designation=designation,
              profile_type='CUSTOM',family='CUSTOM',confidence=1.0,
              reason='Maatwerkdoorsnede uit exact bronprofiel; afzonderlijke materiaal- en productiebeoordeling vereist.')
    return replace(report,profile=profile,evidence=(*report.evidence,
          ('custom_section','source-native-parametric-section'),('custom_section_id',report.section.section_id),
          ('custom_section_dimensions_mm',f'{report.section.width_mm:g}x{report.section.height_mm:g}')))
