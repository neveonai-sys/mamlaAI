import { useEffect, useRef } from 'react';
import { useDispatch } from 'react-redux';
import { clearUser } from '../../features/userSlice';
import { useNavigate } from 'react-router-dom';
import AxiosInstance from '../common/AxiosInstance'; // Adjust the import path accordingly
import React from 'react';

const InactivityHandler = ({ children }) => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const timeoutRef = useRef(null);

  const INACTIVITY_LIMIT = 60 * 60 * 100000;

  const resetTimer = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(handleLogout, INACTIVITY_LIMIT);
  };

  const handleLogout = async () => {
    try {
      await AxiosInstance.post('users/sign-out-user/',{
        scope: "local",
      });
    } catch (error) {
      console.error('Error during logout:', error);
    } finally {
      dispatch(clearUser());
      navigate('/login');
    }
  };

  useEffect(() => {
    window.addEventListener('mousemove', resetTimer);
    window.addEventListener('keypress', resetTimer);
    window.addEventListener('scroll', resetTimer);
    window.addEventListener('click', resetTimer);

    resetTimer(); // Initialize the timer

    return () => {
      window.removeEventListener('mousemove', resetTimer);
      window.removeEventListener('keypress', resetTimer);
      window.removeEventListener('scroll', resetTimer);
      window.removeEventListener('click', resetTimer);
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  return children;
};

export default InactivityHandler;
