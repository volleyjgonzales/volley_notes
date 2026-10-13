"""Tests for semantic action-map comparison; run with unittest discovery."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import re
import shutil
import xml.etree.ElementTree as ET

from compare_agvhito_action_maps import (
    build_diff, compare_actions, cpp_tokens, load_folder, normalize_record, split_routes,
    connected_dot, render_connected,
)


def record(factory='MakeStopPauseAction', args='', hook='OnExit', path=None, line=10):
    return normalize_record({'state': 'alpha', 'cpp_class': 'AlphaState', 'hook': hook,
        'factory': factory, 'arguments': args, 'expression': f'{factory}({args})',
        'line': line, 'source': 'src/sm/alpha.cpp',
        'call_path': path or [f'AlphaState::{hook}']})


def folder(records=None, edges=None):
    return {'folder': '/fixture', 'records': records or [], 'model': {
        'states': [{'name': 'alpha', 'cpp_class': 'AlphaState', 'kind': 'lifecycle',
                    'constant': 'kStateAlpha', 'transition_map': 'kAlphaTransitions'}],
        'edges': edges or [], 'terminal_outcomes': ['terminal'], 'initial_state': 'alpha'}}


class CompareTests(unittest.TestCase):
    def test_line_and_helper_anchor_changes_are_ignored(self):
        before = record(path=['AlphaState::OnExit', 'StopPauseAndSettle@src/sm/a.cpp:10'])
        after = record(path=['AlphaState::OnExit', 'StopPauseAndSettle@src/sm/a.cpp:200'], line=200)
        self.assertEqual(compare_actions([before], [after])[0]['status'], 'unchanged')

    def test_helper_extraction_is_retained_with_path_change(self):
        before = record()
        after = record(path=['AlphaState::OnExit', 'StopPauseAndSettle@src/sm/a.cpp:20'])
        rows = compare_actions([before], [after])
        self.assertEqual([r['status'] for r in rows], ['modified'])

    def test_duplicate_counts_are_preserved(self):
        rows = compare_actions([record(), record()], [record()])
        self.assertEqual([r['status'] for r in rows], ['unchanged', 'removed'])

    def test_identical_helper_match_is_preferred(self):
        direct = record()
        indirect = record(path=['AlphaState::OnExit', 'StopPauseAndSettle'])
        rows = compare_actions([direct, indirect], [indirect])
        self.assertEqual([r['status'] for r in rows], ['removed', 'unchanged'])

    def test_localizing_uploaded_sequence_is_preserved_in_connected_diagram(self):
        # Reproduces the uploaded inventory: main enables the map; feat stops
        # pause through the helper before enabling it. Old output appended +stop.
        enable = normalize_record({
            'state': 'alpha', 'cpp_class': 'AlphaState', 'hook': 'OnEntry',
            'sequence': 1, 'factory': 'MakeEnableMapAction',
            'arguments': 'localization_map_id, kHitoMapVersion',
            'call_path': ['AlphaState::OnEntry']})
        stop = normalize_record({
            'state': 'alpha', 'cpp_class': 'AlphaState', 'hook': 'OnEntry',
            'sequence': 1, 'factory': 'MakeStopPauseAction', 'arguments': '',
            'call_path': ['AlphaState::OnEntry',
                          'StopPauseAndSettle@src/sm/localizing_state.cpp:34']})
        feature_enable = dict(enable, sequence=2)
        diff = build_diff(folder([enable]), folder([stop, feature_enable]))
        rows = diff['states'][0]['sections']['OnEntry']
        self.assertEqual([r['status'] for r in rows], ['added', 'unchanged'])
        dot = connected_dot(diff, [], 'main', False)
        self.assertLess(dot.index('MakeStopPauseAction()'),
                        dot.index('MakeEnableMapAction('))
        self.assertNotIn('[main ', dot)

    def test_middle_insertion_preserves_feature_order(self):
        a, b, c = [record(name) for name in
                   ('MakeCancelOrderAction', 'MakeStopPauseAction', 'MakeMapAction')]
        rows = compare_actions([a, c], [a, b, c])
        self.assertEqual([r['status'] for r in rows], ['unchanged', 'added', 'unchanged'])
        self.assertEqual([r['new_sequence'] for r in rows], [1, 2, 3])
        self.assertEqual([r['new'] for r in rows if r['new']], [a, b, c])

    def test_ordered_projections_with_duplicates_and_reordering(self):
        from itertools import product
        a, b = record('MakeMapAction'), record('MakeStopPauseAction')
        sequences = [list(p) for length in range(4)
                     for p in product((a, b), repeat=length)]
        for old in sequences:
            for new in sequences:
                rows = compare_actions(old, new)
                self.assertEqual([r['old'] for r in rows if r['old']], old)
                self.assertEqual([r['new'] for r in rows if r['new']], new)
                self.assertEqual([r['old_sequence'] for r in rows if r['old']],
                                 list(range(1, len(old) + 1)))
                self.assertEqual([r['new_sequence'] for r in rows if r['new']],
                                 list(range(1, len(new) + 1)))

    def test_argument_change_is_delete_and_add(self):
        rows = compare_actions([record('MakeSoftEStopAction', 'true')],
                               [record('MakeSoftEStopAction', 'false')])
        self.assertEqual([r['status'] for r in rows], ['removed', 'added'])

    def test_whitespace_ignored_but_string_content_preserved(self):
        self.assertEqual(cpp_tokens('a, false'), cpp_tokens(' a ,  false '))
        self.assertNotEqual(cpp_tokens('"two  spaces"'), cpp_tokens('"two spaces"'))
        self.assertNotEqual(cpp_tokens('a + + b'), cpp_tokens('a++b'))

    def test_hook_move_is_delete_and_add(self):
        diff = build_diff(folder([record(hook='OnEntry')]), folder([record(hook='OnExit')]))
        self.assertEqual(diff['summary']['actions'], {'removed': 1, 'added': 1})

    def test_changed_destination_is_delete_and_add(self):
        before = {'source': 'alpha', 'outcome': 'recovered', 'destination': 'alpha'}
        after = dict(before, destination='terminal')
        diff = build_diff(folder(edges=[before]), folder(edges=[after]))
        self.assertEqual(diff['summary']['routes'], {'removed': 1, 'added': 1})

    def test_class_change_is_reported(self):
        before = folder()
        after = copy.deepcopy(before)
        after['model']['states'][0]['cpp_class'] = 'RenamedState'
        diff = build_diff(before, after)
        self.assertEqual(diff['states'][0]['status'], 'modified')
        self.assertEqual(diff['states'][0]['changed_fields'], ['cpp_class'])

    def test_state_addition_and_deletion_are_reported(self):
        before = folder([record()])
        after = folder()
        after['model']['states'][0]['name'] = 'beta'
        after['model']['states'][0]['cpp_class'] = 'BetaState'
        after['model']['initial_state'] = 'beta'
        diff = build_diff(before, after)
        self.assertEqual(diff['summary']['states'], {'removed': 1, 'added': 1})
        self.assertEqual(diff['summary']['actions'], {'removed': 1})

    def test_identical_inventories_have_no_semantic_changes(self):
        before = folder([record()])
        after = copy.deepcopy(before)
        after['model']['metadata'] = {'branch': 'feat', 'generated_at': 'different'}
        diff = build_diff(before, after)
        self.assertEqual(diff['summary']['states'], {'unchanged': 1})
        self.assertEqual(diff['summary']['actions'], {'unchanged': 1})

    def test_factory_reorder_is_flagged(self):
        first = record('MakeCancelOrderAction')
        second = record('MakeStopPauseAction')
        diff = build_diff(folder([first, second]), folder([second, first]))
        self.assertEqual(diff['states'][0]['factory_order_changed'], ['OnExit'])
        self.assertEqual(diff['summary']['actions'], {'removed': 1, 'unchanged': 1, 'added': 1})

    def test_legacy_inventory_hook_and_private_helper(self):
        r = normalize_record({'state': 'alpha', 'cpp_class': 'AlphaState',
            'method': 'VerifiedUnpause', 'lifecycle_hook': 'OnEntry -> VerifiedUnpause',
            'factory': 'MakeStopPauseAction', 'arguments': ''})
        self.assertEqual(r['hook'], 'OnEntry')
        self.assertEqual(r['normalized_path'], ['AlphaState::OnEntry', 'AlphaState::VerifiedUnpause'])

    def test_missing_topology_has_clear_error(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'Regenerate'):
                load_folder(Path(directory))

    def test_folder_reads_full_model_not_split_views(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            (p/'agvhito-action-model.json').write_text(json.dumps(folder()['model']))
            (p/'agvhito-action-inventory.json').write_text(json.dumps([record()]))
            loaded = load_folder(p)
            self.assertEqual(len(loaded['records']), 1)
            self.assertEqual(loaded['model']['states'][0]['name'], 'alpha')

    def test_cancellation_is_split_without_losing_routes(self):
        routes = [{'source': 'alpha', 'outcome': 'canceled', 'destination': 'terminal'},
                  {'source': 'alpha', 'outcome': 'recovered', 'destination': 'alpha'}]
        diff = build_diff(folder(edges=routes), folder(edges=routes))
        groups = split_routes(diff, True)
        self.assertEqual(len(groups['main']), 1)
        self.assertEqual(len(groups['cancellation']), 1)
        self.assertEqual(sum(map(len, groups.values())), 2)

    def test_connected_nodes_are_not_repeated_for_each_route(self):
        routes = [{'source': 'alpha', 'outcome': 'again', 'destination': 'alpha'},
                  {'source': 'alpha', 'outcome': 'done', 'destination': 'terminal'}]
        diff = build_diff(folder(edges=routes), folder(edges=routes))
        dot = connected_dot(diff, diff['routes'], 'main', False)
        self.assertEqual(dot.count('id="state-alpha"'), 1)
        self.assertEqual(len(re.findall(r'^"alpha" -> ', dot, re.M)), 2)

    def test_removed_action_is_red_and_struck_added_is_green(self):
        diff = build_diff(folder([record('MakeSoftEStopAction', 'true')]),
                          folder([record('MakeCancelOrderAction')]))
        dot = connected_dot(diff, [], 'main', False)
        self.assertIn('<S>− MakeSoftEStopAction(true)</S>', dot)
        self.assertIn('COLOR="#BE123C"', dot)
        self.assertIn('<B>+ MakeCancelOrderAction()</B>', dot)
        self.assertIn('COLOR="#15803D"', dot)
        self.assertNotIn('[main ', dot)
        self.assertNotIn('/ feat ', dot)

    def test_retained_factory_with_new_helper_is_not_struck(self):
        diff = build_diff(folder([record()]), folder([record(path=['AlphaState::OnExit', 'StopPauseAndSettle'])]))
        dot = connected_dot(diff, [], 'main', False)
        self.assertNotIn('<S>− MakeStopPauseAction()', dot)
        self.assertIn('MakeStopPauseAction()', dot)
        self.assertIn('+ via AlphaState::OnExit → StopPauseAndSettle', dot)

    def test_html_labels_escape_cpp_and_parse_as_xml(self):
        diff = build_diff(folder(), folder([record('MakeCustomAction', 'a < b && name == "x"')]))
        dot = connected_dot(diff, [], 'main', False)
        labels = re.findall(r'label=<(<TABLE.*?</TABLE>)>', dot)
        self.assertGreaterEqual(len(labels), 2)
        for label in labels:
            ET.fromstring(label)
        self.assertIn('a &lt; b &amp;&amp;', dot)

    @unittest.skipUnless(shutil.which('dot'), 'Graphviz dot executable unavailable')
    def test_graphviz_connected_png_and_svg(self):
        diff = build_diff(folder([record('MakeSoftEStopAction', 'true')]), folder())
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'diff.dot'
            p.write_text(connected_dot(diff, [], 'main', False))
            render_connected(p, 72)
            self.assertTrue(p.with_suffix('.png').is_file())
            svg = p.with_suffix('.svg').read_text()
            self.assertIn('state-alpha', svg)
            self.assertIn('line-through', svg)


if __name__ == '__main__':
    unittest.main()
