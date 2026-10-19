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
  num: '01' | '02' | '03' | '04' | '05' | '06' | '07';
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
    file: 'src/content/01-background.html',
    prefix: 'bg',
    tab: 'Background',
    summary: 'The scheduler as a whole: its five-stage pipeline, the garage model, the data of one plan call, and how to work with the code.',
    parts: [
      { title: 'Orientation', first: 'bg-what-problem-does-this-software-solve' },
      { title: 'Data and objects', first: 'bg-the-garage-model-in-code' },
      { title: 'Working with the code', first: 'bg-packages-build-system-and-dependencies' },
    ],
  },
  {
    key: 'layout-file',
    num: '02',
    file: 'src/content/02-layout-file.html',
    prefix: 'ly',
    tab: 'Layout file',
    summary: 'The site layout YAML field by field: what each key means, who reads it, what the parser checks, and what could be better.',
  },
  {
    key: 'task-planning',
    num: '03',
    file: 'src/content/03-task-planning.html',
    prefix: 'tp',
    tab: 'Task planning',
    summary: 'Stages 1-3: job expansion, tray assignment and AGV assignment build the event DAG.',
  },
  {
    key: 'motion-planning',
    num: '04',
    file: 'src/content/04-motion-planning.html',
    prefix: 'mp',
    tab: 'Motion planning',
    summary: 'Stage 4: CHUGG and SIPP turn the event DAG into timed, collision-free motions.',
  },
  {
    key: 'action-graph',
    num: '05',
    file: 'src/content/05-action-graph.html',
    prefix: 'ag',
    tab: 'Action graph',
    summary: 'Stage 5: action dependency graphs from first principles, the action DAG the scheduler sends, and a review of the pipeline.',
    parts: [
      { title: 'Action dependency graphs from scratch', first: 'ad-why-a-timed-plan-is-not-enough' },
      { title: 'The action DAG in the scheduler', first: 'ad-the-adg-in-our-software' },
      { title: 'Looking back over the pipeline', first: 'bg-faq-design-questions' },
    ],
  },
  {
    key: 'proposal',
    num: '06',
    file: 'src/content/06-issue-and-proposal.html',
    prefix: 'pr',
    tab: 'Issue & proposal',
    summary: 'The refactor: where the code is, what changes, module layout, solver interfaces, staged plan, and proposed naming work.',
  },
  {
    key: 'verification',
    num: '07',
    file: 'src/content/07-verification.html',
    prefix: 'vr',
    tab: 'Verification',
    summary: 'Regression parity and benchmarks for the extracted solvers.',
  },
];

export const docByNum = (num: string) => DOCS.find((d) => d.num === num);
