import { useState, useEffect } from 'react';
import LoginPage from './Login';
import Dashboard from './Dashboard';
import axios from 'axios';
import logo from './assets/logo.png';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [userInfo, setUserInfo] = useState(null);

  const LoadingScreen = () => (
    <div className='h-screen flex flex-col'>
      <header className='bg-blue-600 text-white p-4 grid grid-cols-[auto_1fr] items-center gap-4'>
        <div className='bg-white p-1 rounded'>
          <a href="https://msft-icl-cooperator.netlify.app/"><img src={logo} alt='Logo' className='w-12 h-12' /></a>
        </div>
        <h1 className='text-xl font-bold'>
          Co-Operator: Automated Repository Management
        </h1>
      </header>
      <div className='flex-grow p-8 text-center flex justify-center items-center'>
        Loading...
      </div>
    </div>
  );

  useEffect(() => {
    const checkAuthentication = async () => {
      try {
        const response = await axios.get('/auth/github/status/', {
          withCredentials: true
        });
        if (response.data && response.data.message === 'API access successful') {
          setIsAuthenticated(true);
          setUserInfo(response.data.user_info);
          localStorage.setItem('githubUserId', response.data.github_user_id);
          localStorage.setItem('githubAccountType', response.data.github_account_type);
        } else {
          setIsAuthenticated(false);
        }
      } catch (error) {
        console.error('Authentication check failed:', error);
        setIsAuthenticated(false);
      } finally {
        setLoading(false);
      }
    };

    checkAuthentication();
  }, []);

  const handleLoginSuccess = (token) => {
    localStorage.setItem('githubToken', token);
    setIsAuthenticated(true);
  };

  if (loading) {
    return <LoadingScreen />;
  }

  if (!isAuthenticated) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  return <Dashboard userInfo={userInfo} />;
}

export default App;
