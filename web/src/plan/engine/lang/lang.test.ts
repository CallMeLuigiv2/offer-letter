import { langPack, python, rust } from './index';
import { card, cleanBackup, plan, step } from '../__fixtures__/plans';

describe('python pack', () => {
  it('previews types for each kind', () => {
    const d = plan({
      data: [
        card('lvl', 'log level', 'one_of', { options: ['info', 'warn'] }),
        card('rec', 'request record', 'parts', { fields: [{ name: 'sent at', type: 'float' }, { name: 'level', data_id: 'lvl' }] }),
        card('recs', 'records', 'many_of', { item: 'rec' }),
        card('n', 'late sends', 'value', { vtype: 'number' }),
        card('cap', 'max in flight', 'outside', { vtype: 'number' }),
      ],
    });
    expect(python.typePreview(d, d.data[0])).toBe('class LogLevel(Enum):\n    INFO = "info"\n    WARN = "warn"');
    expect(python.typePreview(d, d.data[1])).toBe('@dataclass\nclass RequestRecord:\n    sent_at: float\n    level: LogLevel');
    expect(python.typePreview(d, d.data[2])).toBe('records: list[RequestRecord]');
    expect(python.typePreview(d, d.data[3])).toBe('late_sends: int');
    expect(python.typePreview(d, d.data[4])).toContain('from outside the code');
  });

  it('derives keyword-safe snake_case function names and drops small words', () => {
    expect(python.fnName('Count the late sends')).toBe('count_late_sends');
    expect(python.fnName('class')).toBe('class_');
    expect(python.fnName('3 retries')).toBe('n_3_retries');
    expect(python.fnName('')).toBe('step');
  });

  it('writes a skeleton with stubs, no logic', () => {
    const s = python.skeleton(cleanBackup());
    expect(s).toContain('def copy_changed_files(files_to_copy: list[File], backup_folder: Path, dry_run_flag: bool) -> int:');
    expect(s).toContain('raise NotImplementedError');
    expect(s).toContain('Raises PermissionError.');
    expect(s).toContain('@dataclass\nclass Summary:');
  });
});

describe('rust pack', () => {
  it('uses & / &mut / owned for the modes', () => {
    const d = plan({ data: [card('l', 'lines', 'many_of', { item: 'text' }), card('n', 'count', 'value', { vtype: 'number' })], steps: [step('a', 'Count the lines', [['l', 'read']], 'n'), step('b', 'Sort the lines', [['l', 'change']], null), step('c', 'Take the lines', [['l', 'consume']], null, { fails: 'raises', raises: 'parse error' })] });
    expect(rust.signature(d, d.steps[0])).toBe('fn count_lines(lines: &[Text]) -> usize');
    expect(rust.signature(d, d.steps[1])).toBe('fn sort_lines(lines: &mut Vec<Text>)');
    expect(rust.signature(d, d.steps[2])).toBe('fn take_lines(lines: Vec<Text>) -> Result<(), ParseError>');
    expect(rust.modes.change.short).toBe('&mut');
    expect(rust.fnName('match')).toBe('match_step');
  });
  it('previews struct and enum and writes todo!() stubs', () => {
    const d = cleanBackup();
    expect(rust.typePreview(d, d.data.find((x) => x.id === 'summary')!)).toBe('struct Summary {\n    copied: usize,\n    skipped: usize,\n}');
    expect(rust.skeleton(d)).toContain('todo!("Copy the changed files")');
    expect(langPack('rust')).toBe(rust);
    expect(langPack('python')).toBe(python);
  });
});
