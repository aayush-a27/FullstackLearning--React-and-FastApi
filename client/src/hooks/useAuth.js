import { useSelector, useDispatch } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import axiosInstance from '../api/axiosInstance';
import { AUTH, USERS } from '../api/endpoints';
import {
  loginStart,
  loginSuccess,
  loginFailure,
  logout as logoutAction,
  updateUser,
  setInitialized,
} from '../features/auth/authSlice';
import { ROUTES } from '../utils/constants';

export function useAuth() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { user, isAuthenticated, isLoading, error } = useSelector(
    (state) => state.auth
  );

  const login = async (email, password) => {
    try {
      dispatch(loginStart());
      const { data } = await axiosInstance.post(AUTH.LOGIN, { email, password });
      localStorage.setItem('accessToken', data.access_token);
      dispatch(
        loginSuccess({
          user: data.user,
          accessToken: data.access_token,
        })
      );
      navigate(ROUTES.DASHBOARD);
    } catch (err) {
      dispatch(loginFailure(err.response?.data?.detail || 'Login failed'));
    }
  };

  const register = async (username, email, password, fullName) => {
    try {
      dispatch(loginStart());
      const { data } = await axiosInstance.post(AUTH.REGISTER, {
        username,
        email,
        password,
        full_name: fullName,
      });
      localStorage.setItem('accessToken', data.access_token);
      dispatch(
        loginSuccess({
          user: data.user,
          accessToken: data.access_token,
        })
      );
      navigate(ROUTES.DASHBOARD);
    } catch (err) {
      dispatch(loginFailure(err.response?.data?.detail || 'Registration failed'));
    }
  };

  const logout = async () => {
    try {
      await axiosInstance.post(AUTH.LOGOUT);
    } catch {
      // Logout even if API call fails
    }
    localStorage.removeItem('accessToken');
    dispatch(logoutAction());
    navigate(ROUTES.LOGIN);
  };

  /** Save a profile/preference change and update the store. */
  const saveProfile = async (changes) => {
    const { data } = await axiosInstance.patch(USERS.UPDATE_PROFILE, changes);
    dispatch(updateUser(data));
    return data;
  };

  /** Permanently delete the account, then return to the login page. */
  const deleteAccount = async (password) => {
    await axiosInstance.delete(USERS.DELETE_ACCOUNT, { data: { password } });
    localStorage.removeItem('accessToken');
    dispatch(logoutAction());
    navigate(ROUTES.LOGIN);
  };

  const fetchUser = async () => {
    try {
      const token = localStorage.getItem('accessToken');
      if (!token) {
        dispatch(setInitialized());
        return;
      }
      const { data } = await axiosInstance.get(USERS.ME);
      dispatch(
        loginSuccess({
          user: data,
          accessToken: token,
        })
      );
    } catch {
      localStorage.removeItem('accessToken');
      dispatch(logoutAction());
    } finally {
      dispatch(setInitialized());
    }
  };

  return {
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    register,
    logout,
    saveProfile,
    deleteAccount,
    fetchUser,
  };
}
