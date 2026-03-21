export type Screen = 'CNR' | 'CASE_STATUS' | 'COURT_ORDERS' | 'CAUSE_LIST' | 'CAVEAT' | 'DASHBOARD' | 'SETTINGS' | 'PROFILE';

export interface NavItem {
  id: Screen;
  label: string;
  icon: string;
}

export interface CaseResult {
  srNo: number;
  caseNumber: string;
  partyName: string;
  orderType?: string;
  date?: string;
  status?: string;
}
