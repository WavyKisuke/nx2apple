        for path in su.PROFILE_PATHS:
            with self.subTest(path=path):
                out = quiet(su.PATCHERS[path], show(self.ref, path))
                left = sorted({m.group(2) for m in su._PROFILE_TOKEN.finditer(out) if m.group(2)})
                self.assertEqual(left, [], f'{path} still reads {left} at compile time')

    def test_the_patched_makefile_uses_one_compiler_spelling(self):
        original = show(self.ref, su.TESTS_MK)
        out = quiet(su.PATCHERS[su.TESTS_MK], original)

        # The upstream test Makefile intentionally contains unrelated compiler recipes using
        # either spelling.  This patcher's contract is only that the fork-added input-map and
        # launcher-contract test targets use one spelling consistently.
        added_targets = [l for l in out.splitlines()
                         if l.startswith('\t') and
                         ('t_input_map.c' in l or 't_launcher_contract.c' in l)]
        self.assertEqual(len(added_targets), 2, added_targets)
        spellings = {'$(CLANG)' if l.startswith('\t$(CLANG) ') else 'clang'
                     for l in added_targets}
        self.assertEqual(len(spellings), 1, added_targets)


class PatchersOnTheLastBase(unittest.TestCase):
    """The patchers must also fit the base the fork was last synced from, so the same code runs before and after a sync."""

    def test_the_patchers_fit_the_last_sync_base(self):
        base = last_base()
        if not base: self.skipTest('the last sync base (.upstream-ref) is not in this repository')
        for path, patcher in su.PATCHERS.items():
            with self.subTest(path=path):
                text = show(base, path)
                self.assertIsNotNone(text)
                try:
                    out = quiet(patcher, text)
                except su.SyncProblem as e:
                    self.fail(f'the patcher does not fit the base {base[:7]}: {e}')