/** The three study documents, in tab order. `file` is relative to the repository root. */
export interface Part {
  title: string;
  /** first and last top-level section number in the part */
  from: number;
  to: number;
}

export interface DocConfig {
  key: string;
  num: '01' | '02' | '03';
  file: string;
  prefix: string;
  tab: string;
  summary: string;
  parts?: Part[];
}

export const DOCS: DocConfig[] = [
  {
    key: 'background',
    num: '01',
    file: '01-software-background.md',
    prefix: 'bg',
    tab: 'Background',
    summary: 'How the existing scheduler works, from the garage model to the response.',
    parts: [
      { title: 'Orientation', from: 1, to: 5 },
      { title: 'Data and objects', from: 6, to: 13 },
      { title: 'Algorithms', from: 14, to: 20 },
      { title: 'Working with the code', from: 21, to: 26 },
    ],
  },
  {
    key: 'proposal',
    num: '02',
    file: '02-issue-and-proposal.md',
    prefix: 'pr',
    tab: 'Issue & proposal',
    summary: 'What the refactor changes and why: solver interfaces, layout, staged plan.',
  },
  {
    key: 'verification',
    num: '03',
    file: '03-verification-plan.md',
    prefix: 'vr',
    tab: 'Verification',
    summary: 'Regression parity and benchmarks for the extracted solvers.',
  },
];

export const docByNum = (num: string) => DOCS.find((d) => d.num === num);
export const docByFile = (file: string) => DOCS.find((d) => d.file === file);
