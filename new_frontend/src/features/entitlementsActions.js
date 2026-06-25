import apiClient from '../services/api';
import { clearEntitlements, setEntitlements } from './entitlementsSlice';

export async function refreshEntitlements(dispatch) {
  try {
    const response = await apiClient.get('users/entitlements/summary/');
    dispatch(setEntitlements(response.data || {}));
    return response.data || {};
  } catch {
    dispatch(clearEntitlements());
    return null;
  }
}