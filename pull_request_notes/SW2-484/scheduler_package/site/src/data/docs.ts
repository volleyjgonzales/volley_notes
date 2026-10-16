/** The study documents, in tab order. `file` is relative to site/. */
export interface Part {
  title: string;
  /** id of the first <h2> in the part; the part runs until the next part */
  first: string;
  /** filled in at build time, e.g. "6–13" */
  range?: string;
}

export interface DocConfig {
  key: string;
  num: '01' | '02' | '03' | '04' | '05';
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
    file: 'src/content/01-software-background.html',
    prefix: 'bg',
    tab: 'Background',
    summary: 'How the existing scheduler works, from the garage model to the response.',
    parts: [
      { title: 'Orientation', first: 'bg-what-problem-does-this-software-solve' },
      { title: 'Data and objects', first: 'bg-the-garage-model-in-code' },
      { title: 'Algorithms', first: 'bg-job-expansion-from-jobs-to-events' },
      { title: 'Working with the code', first: 'bg-packages-build-system-and-dependencies' },
    ],
  },
  {
    key: 'proposal',
    num: '02',
    file: 'src/content/02-issue-and-proposal.html',
    prefix: 'pr',
    tab: 'Issue & proposal',
    summary: 'What the refactor changes and why: solver interfaces, layout, staged plan.',
  },
  {
    key: 'verification',
    num: '03',
    file: 'src/content/03-verification-plan.html',
    prefix: 'vr',
    tab: 'Verification',
    summary: 'Regression parity and benchmarks for the extracted solvers.',
  },
  {
    key: 'naming',
    num: '04',
    file: 'src/content/04-naming.html',
    prefix: 'nm',
    tab: 'Naming',
    summary: 'Renames and small struct refactors across messages, common_ros, planner_core and the scheduler.',
  },
  {
    key: 'adg',
    num: '05',
    file: 'src/content/05-adg-primer.html',
    prefix: 'ad',
    tab: 'ADG primer',
    summary: 'Action dependency graphs from scratch: orders, construction, safe execution, timing, and the schedule the scheduler sends.',
  },
];

export const docByNum = (num: string) => DOCS.find((d) => d.num === num);
