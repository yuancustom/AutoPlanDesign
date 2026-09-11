#!/usr/bin/env python3
"""Regression tests for the two helper validators, not building reconstruction tests.

Run from the skill root: python -m unittest discover -s scripts -p 'test_*.py' -v
Test geometry is synthetic and must not be delivered as an actual building.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
import struct
import tempfile
import unittest

from validate_project import validate_project
from validate_deliverables import parse_glb, validate_deliverables

ROOT = Path(__file__).resolve().parents[1]


def valid_project() -> dict:
    data = json.loads((ROOT / 'assets/project.template.json').read_text(encoding='utf-8'))
    values = {'overall_x_m':50,'overall_y_m':30,'base_elevation_m':0,
              'floor_h_1_m':4,'floor_h_2_m':3,'floor_h_3_m':3,
              'height_reference':'floor_to_floor_then_roof_datum'}
    for key,value in values.items():
        data['facts'][key].update(value=value,status='user_confirmed',approval='confirmed',
                                  source_refs=['test:synthetic-confirmed-input'],confidence='high')
    return data


def write_glb_header(path: Path, header: dict) -> None:
    payload=json.dumps(header,separators=(',',':')).encode('utf-8')
    payload += b' ' * ((-len(payload)) % 4)
    path.write_bytes(struct.pack('<4sII',b'glTF',2,20+len(payload))+struct.pack('<II',len(payload),0x4E4F534A)+payload)


def create_fixture(directory: Path) -> None:
    """Only for file-reader tests: rectangles/cuboids, NOT the H-shaped building."""
    import ezdxf
    import numpy as np
    import trimesh
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    directory.mkdir(parents=True,exist_ok=True)
    doc=ezdxf.new('R2010')
    doc.units=4
    msp=doc.modelspace()
    for i in range(3):
        name=f'F{i+1:02d}_A-OUTLINE'
        doc.layers.new(name)
        x=i*60000
        msp.add_lwpolyline([(x,0),(x+50000,0),(x+50000,30000),(x,30000)],close=True,dxfattribs={'layer':name})
        msp.add_text(f'F{i+1:02d} SYNTHETIC TEST',dxfattribs={'height':300,'insert':(x,32000)})
    doc.saveas(directory/'TEST_plans_mm.dxf')
    pdf=canvas.Canvas(str(directory/'TEST_drawings.pdf'),pagesize=(420*mm,297*mm))
    for i,h in enumerate((4,3,3)):
        pdf.setFont('Helvetica-Bold',16)
        pdf.drawString(25*mm,270*mm,f'F{i+1:02d} | File-reader test fixture')
        pdf.setFont('Helvetica',10)
        pdf.drawString(25*mm,260*mm,'Synthetic rectangle only. NOT a reconstructed building. NOT for design use.')
        pdf.setLineWidth(.6)
        pdf.rect(40*mm,70*mm,250*mm,150*mm)
        pdf.drawString(40*mm,59*mm,'Nominal outline: 50 m x 30 m; plot fixture at 1:200; 100% print size.')
        pdf.drawString(40*mm,50*mm,f'Test floor-to-floor height: {h} m. No architectural review performed.')
        pdf.showPage()
    pdf.save()
    scene=trimesh.Scene()
    R=np.array([[1,0,0,0],[0,0,1,0],[0,-1,0,0],[0,0,0,1]],dtype=float)
    z=0
    for i,h in enumerate((4,3,3)):
        box=trimesh.creation.box(extents=[50,30,h])
        box.apply_translation([25,15,z+h/2])
        box.apply_transform(R)
        scene.add_geometry(box,node_name=f'F{i+1:02d}_SYNTHETIC_CUBOID',geom_name=f'TEST_{i}')
        z+=h
    scene.metadata={'purpose':'file-reader test only, not building reconstruction'}
    scene.export(str(directory/'TEST_model_m.glb'))


class ProjectTests(unittest.TestCase):
    def test_valid_input_levels(self):
        report=validate_project(valid_project())
        self.assertEqual(report['exit_code'],0,report['errors'])
        self.assertEqual([x['elevation_m'] for x in report['derived']['floor_levels']],[0,4,7])
        self.assertEqual(report['derived']['roof_datum_m'],10)
    def test_case_must_keep_pending_decisions(self):
        case=json.loads((ROOT/'assets/project.h50x30-draft.json').read_text(encoding='utf-8'))
        report=validate_project(case)
        self.assertEqual(report['exit_code'],2)
        codes={e['code'] for e in report['errors']}
        self.assertIn('TOPOLOGY_NOT_APPROVED',codes)
        self.assertIn('CHANGE_PENDING',codes)
    def test_unknown_scale_blocks(self):
        d=valid_project();d['facts']['overall_x_m'].update(value=None,status='unknown',approval='pending')
        self.assertEqual(validate_project(d)['exit_code'],2)
    def test_height_zero_blocks(self):
        d=valid_project();d['facts']['floor_h_1_m']['value']=0
        self.assertIn('POSITIVE',{x['code'] for x in validate_project(d)['errors']})
    def test_bool_is_not_height(self):
        d=valid_project();d['facts']['floor_h_1_m']['value']=True
        self.assertIn('REQUIRED_NUMBER',{x['code'] for x in validate_project(d)['errors']})
    def test_clear_height_cannot_be_used_as_floor_height(self):
        d=valid_project();d['facts']['height_reference']['value']='clear_height'
        self.assertIn('HEIGHT_REFERENCE',{x['code'] for x in validate_project(d)['errors']})
    def test_additional_output_format_blocks(self):
        d=valid_project();d['outputs']['formats'].append('step')
        self.assertIn('OUTPUT_FORMATS',{x['code'] for x in validate_project(d)['errors']})
    def test_copied_options_not_a_selection(self):
        d=valid_project();d['policies']['footprint']['mode']='preserve / normalize'
        self.assertIn('POLICY_MODE',{x['code'] for x in validate_project(d)['errors']})
    def test_approval_without_evidence_blocks_change(self):
        d=valid_project();d['policies']['stair'].update(mode='align',approval='confirmed',approval_ref=None)
        self.assertIn('APPROVAL_EVIDENCE',{x['code'] for x in validate_project(d)['errors']})
    def test_fact_dependency_cycle(self):
        d=valid_project();d['facts']['overall_x_m']['depends_on']=['overall_y_m'];d['facts']['overall_y_m']['depends_on']=['overall_x_m']
        self.assertIn('DEPENDENCY_CYCLE',{x['code'] for x in validate_project(d)['errors']})
    def test_unknown_dependency_cannot_be_laundered(self):
        d=valid_project();d['facts']['floor_h_1_m'].update(status='derived',depends_on=['external_wall_m'])
        self.assertIn('REQUIRED_UNKNOWN',{x['code'] for x in validate_project(d)['errors']})
    def test_single_reference_length_is_allowed(self):
        d=valid_project();d['building']['scale']={'mode':'reference_length','fact_ids':['overall_x_m']}
        d['facts']['overall_y_m'].update(value=None,status='unknown',approval='pending')
        self.assertEqual(validate_project(d)['exit_code'],0)
    def test_missing_source_paths_requested(self):
        self.assertIn('SOURCE_NOT_FOUND',{x['code'] for x in validate_project(valid_project(),Path('/definitely/nonexistent'),True)['errors']})
    def test_root_type(self):
        self.assertEqual(validate_project([])['exit_code'],2)


class FileTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='floorplan-skill-test-')
        self.directory=Path(self.temp.name)/'deliverables'
        create_fixture(self.directory)
    def tearDown(self):
        self.temp.cleanup()
    def test_valid_files_are_only_file_level_pass(self):
        report=validate_deliverables(self.directory)
        self.assertEqual(report['exit_code'],0,report['errors'])
        self.assertIn('cross-format geometry equivalence',report['not_checked'])
        self.assertEqual(report['checks']['TEST_drawings.pdf']['page_count'],3)
    def test_extra_readme_is_not_a_deliverable(self):
        (self.directory/'README.md').write_text('not allowed',encoding='utf-8')
        self.assertIn('EXTRA_FORMAT',{x['code'] for x in validate_deliverables(self.directory)['errors']})
    def test_missing_file_blocks(self):
        (self.directory/'TEST_model_m.glb').unlink()
        self.assertIn('FILE_COUNT',{x['code'] for x in validate_deliverables(self.directory)['errors']})
    def test_corrupt_glb_header_blocks(self):
        (self.directory/'TEST_model_m.glb').write_bytes(b'NOT_A_GLB_FILE')
        self.assertIn('GLB_READ',{x['code'] for x in validate_deliverables(self.directory)['errors']})
    def test_external_resource_blocks_before_load(self):
        file=self.directory/'TEST_model_m.glb'
        write_glb_header(file,{'asset':{'version':'2.0'},'buffers':[{'byteLength':4,'uri':'https://invalid.example/external.bin'}]})
        with self.assertRaisesRegex(ValueError,'External resource'):
            parse_glb(file)
    def test_node_cycle_blocks(self):
        file=self.directory/'TEST_model_m.glb'
        write_glb_header(file,{'asset':{'version':'2.0'},'nodes':[{'children':[1]},{'children':[0]}],'scenes':[{'nodes':[0]}]})
        with self.assertRaisesRegex(ValueError,'cycle'):
            parse_glb(file)
    def test_wrong_dxf_units_blocks(self):
        import ezdxf
        file=self.directory/'TEST_plans_mm.dxf';d=ezdxf.readfile(file);d.units=6;d.saveas(file)
        self.assertIn('DXF_UNITS',{x['code'] for x in validate_deliverables(self.directory)['errors']})
    def test_text_only_pdf_is_rejected(self):
        from reportlab.pdfgen import canvas
        file=self.directory/'TEST_drawings.pdf';c=canvas.Canvas(str(file));c.drawString(30,700,'No vector plan here');c.save()
        self.assertIn('PDF_NO_VECTORS',{x['code'] for x in validate_deliverables(self.directory)['errors']})


class PackagingTests(unittest.TestCase):
    def test_templates_conform_to_schema(self):
        import jsonschema
        schema=json.loads((ROOT/'assets/project.schema.json').read_text(encoding='utf-8'))
        jsonschema.Draft202012Validator.check_schema(schema)
        for name in ['project.template.json','project.h50x30-draft.json']:
            jsonschema.validate(json.loads((ROOT/'assets'/name).read_text(encoding='utf-8')),schema)
    def test_skill_frontmatter(self):
        text=(ROOT/'SKILL.md').read_text(encoding='utf-8')
        self.assertTrue(text.startswith('---\n'))
        self.assertIn('name: '+ROOT.name,text.split('---',2)[1])
        self.assertLess(len(text.splitlines()),500)

if __name__=='__main__':
    unittest.main()
