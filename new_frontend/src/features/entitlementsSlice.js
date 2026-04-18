import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  planCode: '',
  launchAccess: '',
  quotaResetAt: '',
  wallet: {
    balance: 0,
    currencyCode: 'INR',
  },
  trial: {
    active: false,
    startedAt: '',
    endsAt: '',
    daysRemaining: 0,
  },
  features: {},
  lastFetchedAt: '',
};

const entitlementsSlice = createSlice({
  name: 'entitlements',
  initialState,
  reducers: {
    setEntitlements(state, action) {
      const payload = action.payload || {};
      state.planCode = payload.plan_code || '';
      state.launchAccess = payload.launch_access || '';
      state.quotaResetAt = payload.quota_reset_at || '';
      state.wallet = {
        balance: payload.wallet?.balance ?? 0,
        currencyCode: payload.wallet?.currency_code || 'INR',
      };
      state.trial = {
        active: Boolean(payload.trial?.active),
        startedAt: payload.trial?.started_at || '',
        endsAt: payload.trial?.ends_at || '',
        daysRemaining: payload.trial?.days_remaining ?? 0,
      };
      state.features = payload.features || {};
      state.lastFetchedAt = new Date().toISOString();
    },
    updateFeatureQuota(state, action) {
      const quota = action.payload || {};
      const featureCode = quota.feature_code;
      if (!featureCode) return;

      state.features = {
        ...state.features,
        [featureCode]: quota,
      };

      if (quota.plan_code) {
        state.planCode = quota.plan_code;
      }
      if (quota.launch_access) {
        state.launchAccess = quota.launch_access;
      }
      if (quota.quota_reset_at) {
        state.quotaResetAt = quota.quota_reset_at;
      }
      if (typeof quota.wallet_credits_balance === 'number') {
        state.wallet = {
          ...state.wallet,
          balance: quota.wallet_credits_balance,
        };
      }
      if (typeof quota.is_trial === 'boolean') {
        state.trial = {
          ...state.trial,
          active: quota.is_trial,
        };
      }
      state.lastFetchedAt = new Date().toISOString();
    },
    clearEntitlements(state) {
      state.planCode = '';
      state.launchAccess = '';
      state.quotaResetAt = '';
      state.wallet = { balance: 0, currencyCode: 'INR' };
      state.trial = { active: false, startedAt: '', endsAt: '', daysRemaining: 0 };
      state.features = {};
      state.lastFetchedAt = '';
    },
  },
});

export const { setEntitlements, updateFeatureQuota, clearEntitlements } = entitlementsSlice.actions;
export default entitlementsSlice.reducer;