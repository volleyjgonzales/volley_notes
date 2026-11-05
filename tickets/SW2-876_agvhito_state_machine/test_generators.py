"""Regression checks for the bounded AGVHITO parser; stdlib unittest only.

Run: python3 -m unittest discover -s . -p test_generators.py -v
Tests construct small C++ source fixtures; no ROS dependencies are needed.
"""
import tempfile
import unittest
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from generate_agvhito_state_machine import parse_package, mask_cpp, diagram_views, subtitle_lines
from generate_agvhito_action_map import audit


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.write('include/agvhito/sm/state_strings.hpp', '''
inline constexpr auto kStateAlpha {"alpha"};
inline constexpr auto kStateBeta {"beta"};
inline constexpr auto kOutcomeGo {"go"};
inline constexpr auto kOutcomePause {"pause-requested"};
inline constexpr auto kOutcomeTerminal {"done"};
inline const yasmin::Transitions kAlphaTransitions {
  {kOutcomeGo, kStateBeta},
  {yasminx::kOutcomeCanceled, kOutcomeTerminal},
};
inline const yasmin::Transitions kBetaTransitions {
  {kOutcomeGo, kStateAlpha},
};
''')
        self.write('src/sm/root.cpp', '''
auto root = std::make_unique<yasminx::RootStateMachine>(
  "root", yasmin::Outcomes {kOutcomeTerminal}, context);
root->add_state(kStateAlpha, std::make_shared<AlphaState>(context), kAlphaTransitions);
root->add_state(kStateBeta, std::make_shared<BetaState>(context), kBetaTransitions);
''')
        self.write('include/agvhito/sm/alpha_state.hpp', '''
class AlphaState : public yasminx::State {
  Result Execute(Board board);
};
''')
        self.write('include/agvhito/sm/beta_state.hpp', '''
class BetaState : public yasminx::LifecycleState {
  Result Step(Board board);
};
''')
        self.write('src/sm/alpha_state.cpp', '''
namespace volley::agvhito::sm {
Result AlphaState::Execute(Board board) {
  // MakeStartPauseAction(); not a real call
  const auto text = R"doc(MakeSoftEStopAction(true); { })doc";
  detail::Outer(board);
  return go;
}
}
''')
        self.write('src/sm/beta_state.cpp', '''
namespace volley::agvhito::sm {
Result BetaState::Step(Board board) { return Continue {}; }
}
''')
        self.write('src/sm/context_utils.cpp', '''
namespace volley::agvhito::sm {
Result Inner(Board board) { return MakeStopPauseAction(); }
}
''')
        self.write('include/agvhito/sm/detail/helper.hpp', '''
namespace volley::agvhito::sm::detail {
inline Result Outer(Board board) { return Inner(board); }
}
''')

    def write(self, name, contents):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)

    def test_helper_argument_actions_precede_helper_body(self):
        self.write('src/sm/alpha_state.cpp', """
namespace volley::agvhito::sm {
Result AlphaState::Execute(Board board) {
  MakeFirstAction();
  Inner(MakeMapAction());
  MakeLastAction();
  return go;
}
}
""")
        records, sections = audit(parse_package(self.root))
        self.assertEqual([r['factory'] for r in records],
                         ['MakeFirstAction', 'MakeMapAction',
                          'MakeStopPauseAction', 'MakeLastAction'])
        self.assertEqual([r['sequence'] for r in sections['alpha']['Execute']],
                         [1, 2, 3, 4])

    def test_initializer_list_and_helper_call_site_order(self):
        self.write('src/sm/alpha_state.cpp', """
namespace volley::agvhito::sm {
Result AlphaState::Execute(Board board) {
  Publish({MakeMapAction(), MakeSecondAction()});
  detail::Outer(board);
  Publish({MakeFinalAction()});
  return go;
}
}
""")
        records, _ = audit(parse_package(self.root))
        self.assertEqual([r['factory'] for r in records],
                         ['MakeMapAction', 'MakeSecondAction',
                          'MakeStopPauseAction', 'MakeFinalAction'])

    def test_registered_names_classes_and_terminal(self):
        model = parse_package(self.root)
        self.assertEqual([s['cpp_class'] for s in model['states']], ['AlphaState', 'BetaState'])
        self.assertEqual([s['kind'] for s in model['states']], ['state', 'lifecycle'])
        self.assertEqual(model['terminal_outcomes'], ['done'])
        self.assertEqual(len(model['edges']), 3)

    def test_indirect_factories_and_empty_lifecycle_sections(self):
        records, sections = audit(parse_package(self.root))
        self.assertEqual([r['factory'] for r in records], ['MakeStopPauseAction'])
        self.assertEqual(records[0]['hook'], 'Execute')
        self.assertEqual(len(records[0]['call_path']), 3)
        self.assertEqual(sections['beta'], {'OnEntry': [], 'Step': [], 'OnExit': []})

    def test_added_transition_is_discovered(self):
        path = self.root / 'include/agvhito/sm/state_strings.hpp'
        path.write_text(path.read_text().replace('{kOutcomeGo, kStateAlpha},',
            '{kOutcomeGo, kStateAlpha},\n  {kOutcomePause, kStateBeta},'))
        model = parse_package(self.root)
        self.assertEqual(len(model['edges']), 4)
        self.assertIn(('beta', 'pause-requested', 'beta'),
            [(e['source'], e['outcome'], e['destination']) for e in model['edges']])

    def test_added_state_is_discovered(self):
        p = self.root / 'include/agvhito/sm/state_strings.hpp'
        p.write_text(p.read_text() + '''
inline constexpr auto kStateGamma {"gamma"};
inline const yasmin::Transitions kGammaTransitions {
  {kOutcomeGo, kStateAlpha},
};
''')
        p = self.root / 'src/sm/root.cpp'
        p.write_text(p.read_text() + 'root->add_state(kStateGamma, std::make_shared<GammaState>(context), kGammaTransitions);')
        self.write('include/agvhito/sm/gamma_state.hpp', 'class GammaState : public yasminx::LifecycleState {};')
        model = parse_package(self.root)
        self.assertEqual(len(model['states']), 3)
        self.assertEqual(len(model['edges']), 4)
        _, sections = audit(model)
        self.assertEqual(sections['gamma'], {'OnEntry': [], 'Step': [], 'OnExit': []})

    def test_removed_helper_action_disappears(self):
        self.write('src/sm/context_utils.cpp', '''
namespace volley::agvhito::sm { Result Inner(Board board) { return {}; } }
''')
        records, _ = audit(parse_package(self.root))
        self.assertEqual(records, [])

    def test_added_step_factory_is_discovered(self):
        self.write('src/sm/beta_state.cpp', '''
namespace volley::agvhito::sm {
Result BetaState::Step(Board board) { MakeStartPauseAction(); return Continue {}; }
}
''')
        records, sections = audit(parse_package(self.root))
        self.assertEqual(sections['beta']['Step'][0]['factory'], 'MakeStartPauseAction')
        self.assertTrue(sections['beta']['Step'][0]['highlight'])

    def test_unaccounted_state_factory_fails(self):
        p = self.root / 'src/sm/alpha_state.cpp'
        p.write_text(p.read_text() + 'auto unexpected = MakeCancelOrderAction();')
        with self.assertRaisesRegex(ValueError, 'not reachable'):
            audit(parse_package(self.root))

    def test_recursive_helper_does_not_loop(self):
        self.write('src/sm/context_utils.cpp', '''
namespace volley::agvhito::sm {
Result Inner(Board board) { detail::Outer(board); return MakeStopPauseAction(); }
}
''')
        model = parse_package(self.root)
        records, _ = audit(model)
        self.assertEqual(len(records), 1)
        self.assertTrue(any('Recursive helper' in w for w in model['warnings']))

    def test_unknown_destination_fails(self):
        p = self.root / 'include/agvhito/sm/state_strings.hpp'
        p.write_text(p.read_text().replace('{kOutcomeGo, kStateBeta}', '{kOutcomeGo, "missing"}'))
        with self.assertRaisesRegex(ValueError, 'Unregistered transition destination'):
            parse_package(self.root)

    def test_duplicate_outcome_fails(self):
        p = self.root / 'include/agvhito/sm/state_strings.hpp'
        p.write_text(p.read_text().replace('{kOutcomeGo, kStateBeta},', '{kOutcomeGo, kStateBeta},\n {kOutcomeGo, kStateAlpha},'))
        with self.assertRaisesRegex(ValueError, 'Duplicate outcome'):
            parse_package(self.root)

    def test_comment_mask_preserves_lines(self):
        text = '// a\nR"tag({fake()})tag"; /* b\nc */ real();'
        masked = mask_cpp(text)
        self.assertEqual(len(text), len(masked))
        self.assertEqual(text.count('\n'), masked.count('\n'))
        self.assertNotIn('fake', masked)
        self.assertIn('real()', masked)

    def test_default_split_hides_cancellation_only_in_view(self):
        model = parse_package(self.root)
        views = diagram_views(model)
        self.assertFalse(any(e['outcome'] == 'canceled' for e in views['main']['edges']))
        self.assertEqual(len(views['cancellation']['edges']), 1)
        self.assertEqual(len(model['edges']), 3)
        self.assertEqual(sum(len(v['edges']) for v in views.values()), 3)

    def test_no_split_keeps_every_route(self):
        model = parse_package(self.root)
        views = diagram_views(model, split=False)
        self.assertEqual(list(views), ['main'])
        self.assertEqual(views['main']['edges'], model['edges'])

    def test_errored_terminal_route_is_in_failure_view(self):
        model = parse_package(self.root)
        edge = {'source': 'beta', 'outcome': 'errored', 'destination': 'done'}
        model['edges'].append(edge)
        views = diagram_views(model)
        self.assertEqual(views['errors']['edges'], [edge])
        self.assertNotIn(edge, views['cancellation']['edges'])

    def test_exported_source_metadata_without_git(self):
        model = parse_package(self.root)
        metadata = model['metadata']
        self.assertIsNone(metadata['commit'])
        self.assertIsNone(metadata['sm_dirty'])
        self.assertIsNotNone(datetime.fromisoformat(metadata['generated_at']).tzinfo)
        self.assertIn('Git unavailable', subtitle_lines(model)[0])

    @unittest.skipUnless(shutil.which('git'), 'Git executable unavailable')
    def test_git_branch_commit_dirty_and_detached_metadata(self):
        def git(*args):
            return subprocess.run(['git', '-C', str(self.root), *args],
                                  check=True, capture_output=True, text=True).stdout.strip()
        git('init', '-b', 'diagram-test')
        git('add', '.')
        git('-c', 'user.name=Parser Test', '-c', 'user.email=parser@example.invalid',
            'commit', '-m', 'test fixture')
        model = parse_package(self.root)
        self.assertEqual(model['metadata']['branch'], 'diagram-test')
        self.assertEqual(model['metadata']['commit'], git('rev-parse', 'HEAD'))
        self.assertEqual(model['metadata']['commit_short'], git('rev-parse', '--short=12', 'HEAD'))
        self.assertFalse(model['metadata']['sm_dirty'])
        p = self.root / 'src/sm/beta_state.cpp'
        p.write_text(p.read_text() + '\n// changed source\n')
        dirty = parse_package(self.root)
        self.assertTrue(dirty['metadata']['sm_dirty'])
        self.assertNotEqual(dirty['source_sha256'], model['source_sha256'])
        git('checkout', '--detach')
        self.assertEqual(parse_package(self.root)['metadata']['branch'], 'detached HEAD')


if __name__ == '__main__':
    unittest.main()
