// Live court intelligence stats + legal news feed shown on the Resources page
// and the /website overview. Static (deterministic) so prerendered HTML is stable.
export const STAT_CARDS = [
  { icon: 'gavel',           value: '4.8', unit: 'Cr', desc: 'Total pending cases across all district & High Courts in India',       source: 'NJDG Live · Updated daily' },
  { icon: 'check_circle',    value: '2.2', unit: 'L',  desc: 'Cases disposed this month across all High Courts and District Courts',  source: 'NJDG Live · Updated monthly' },
  { icon: 'account_balance', value: '72',  unit: 'K',  desc: 'Pending matters before the Supreme Court of India',                    source: 'SCI Portal · Updated weekly' },
  { icon: 'today',           value: '68',  unit: '',   desc: "Items on today's Supreme Court cause list",                            source: 'SC Daily Cause List' },
];

export const NEWS_ITEMS = [
  { source: 'LiveLaw', tone: 'bg-primary/20 text-primary-soft',    text: 'SC bench issues directions on undertrial prisoners; seeks state compliance reports', time: '2 hours ago' },
  { source: 'B&B',     tone: 'bg-amber-500/20 text-amber-300',     text: 'Delhi HC: landlord cannot evict tenant without compliance of Rent Control Act provisions', time: '4 hours ago' },
  { source: 'SCI',     tone: 'bg-emerald-500/20 text-emerald-400', text: 'Constitution bench to take up PMLA provisions challenge; listed for July arguments', time: 'Yesterday' },
  { source: 'LiveLaw', tone: 'bg-primary/20 text-primary-soft',    text: 'BCI issues advisory on Bar Council elections; sets deadline for state bar council compliance', time: 'Yesterday' },
];
