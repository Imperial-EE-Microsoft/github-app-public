import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import logo from './assets/logo.png';

function Dashboard() {
  const [repositories, setRepositories] = useState([]);
  const [openDropdown, setOpenDropdown] = useState(null);
  const [notification, setNotification] = useState({
    message: '',
    repoName: '',
    errorType: null, // if error is blank then the notf is coloured blue else red
  });
  const [showNotification, setShowNotification] = useState(false); // New state to control alert visibility
  const [isAnyRepoInUse, setIsAnyRepoInUse] = useState(false); // New state to track if any repo is in use
  const dropdownRefs = useRef([]);

  const csrfToken = getCookie('csrftoken');

  const setMonitoringStatus = (repoId, status) => {
    const url = `/translate/repos/monitor/${repoId}/${status ? 'true' : 'false'}/`;
    const githubUserId = localStorage.getItem('githubUserId');
    const githubAccountType = localStorage.getItem('githubAccountType');
    const repoName = repositories.find(repo => repo.id === repoId)?.name;

    setRepositories(
      repositories.map(repo =>
        repo.id === repoId
          ? { ...repo, inUse: status ? 'Initialising...' : 'Turning Off...' }
          : repo
      )
    );

    // Update the isAnyRepoInUse state
    setIsAnyRepoInUse(true);

    axios
      .post(
        url,
        {
          github_id: githubUserId,
          github_account_type: githubAccountType,
        },
        {
          headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json',
          },
          timeout: 0,
        }
      )
      .then(response => {
        const { message, branch_url } = response.data;
        setRepositories(
          repositories.map(repo =>
            repo.id === repoId
              ? { ...repo, inUse: status ? 'Active' : 'Inactive' }
              : repo
          )
        );
        setOpenDropdown(null);
        setIsAnyRepoInUse(false); // Update the state to false after the operation is completed
        if (status && branch_url) {
          setNotification({
            message: `<p>${message} View the branch <a href="${branch_url}" target="_blank" rel="noopener noreferrer" class="underline">here.</a></p>`,
            repoName: repoName,
            errorType: null,
          });
          setShowNotification(true);
        } else if (!status) {
          setNotification({
            message: `Monitoring turned off successfully for "${repoName}".`,
            repoName: repoName,
            errorType: null,
          });
          setShowNotification(true);
        }
      })
      .catch(error => {
        console.error('Error setting monitoring status:', error);
        setNotification({
          message: `Process failed for "${repoName}". Please try again.`,
          repoName: repoName,
          errorType: 'error',
        });
        setShowNotification(true);
        updateDashboardTable();
        setIsAnyRepoInUse(false); // Update the state to false if there's an error
      });
  };

  const updateDashboardTable = () => {
    const githubUserId = localStorage.getItem('githubUserId');
    const githubAccountType = localStorage.getItem('githubAccountType');

    axios
      .get('/translate/repos/', {
        headers: {
          'X-Github-User-Id': githubUserId,
          'X-Github-Account-Type': githubAccountType,
          'X-CSRFToken': csrfToken, // Include CSRF token if required for GET requests
        },
      })
      .then(response => {
        console.log('Repositories:', response.data.repositories);
        const repos = response.data.repositories.map(repo => ({
          id: repo.repo_id,
          name: repo.repo_name,
          url: repo.repo_url,
          inUse: repo.monitored ? 'Active' : 'Inactive',
        }));
        setRepositories(repos);
      })
      .catch(error => {
        console.error('Error refreshing repositories:', error);
        setNotification({
          message: 'Failed to refresh repository list. Please try again.',
          repoName: '',
          errorType: 'updateError',
        });
        setShowNotification(true);
      });
  };

  useEffect(() => {
    refreshRepos();
    updateDashboardTable(); // Fetch repositories when the component mounts
  }, []);

  const refreshRepos = () => {
    const githubUserId = localStorage.getItem('githubUserId');
    const githubAccountType = localStorage.getItem('githubAccountType');

    fetch('/api/refresh/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify({
        'X-Github-Id': githubUserId,
        'X-Github-Account-Type': githubAccountType,
      }),
    })
      .then(response => response.json())
      .then(data => {
        updateDashboardTable(); // Call to refresh the repository list
      })
      .catch(error => {
        console.error('Error triggering refresh:', error);
        setNotification({
          message: `Failed to fetch repositories from GitHub. Please try again.`,
          repoName: '',
          errorType: 'refreshError',
        });
        setShowNotification(true);
      });
  };

  const toggleDropdown = index => {
    setOpenDropdown(openDropdown === index ? null : index);
  };

  useEffect(() => {
    function handleClickOutside(event) {
      if (
        openDropdown !== null &&
        dropdownRefs.current[openDropdown] &&
        !dropdownRefs.current[openDropdown].contains(event.target)
      ) {
        setOpenDropdown(null);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [openDropdown]);

  const dismissError = () => {
    setShowNotification(false);
    setNotification({ message: '', repoName: '', errorType: null });
  };

  return (
    <div className='flex flex-col h-screen'>
      <header className='bg-blue-600 text-white p-4 grid grid-cols-[auto_1fr] items-center gap-4'>
        <div className='bg-white p-1 rounded'>
          <a href='https://msft-icl-cooperator.netlify.app/'>
            <img src={logo} alt='Logo' className='w-12 h-12' />
          </a>
        </div>
        <div className='flex gap-2 items-center'>
          <h1 className='text-xl font-bold'>
            Co-Operator: Automated Repository Management
          </h1>
          <div className='flex-grow '></div>
          <a
            href='https://msft-icl-cooperator.netlify.app/'
            className='text-white text-right pr-4 font-bold'
          >
            About
          </a>
        </div>
      </header>

      <div className='flex-grow container mx-auto p-8 overflow-visible'>
        <div className='flex justify-between items-center mb-4'>
          <h1 className='text-2xl font-bold'>Repositories</h1>
          <button
            className={`bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-4 rounded ${
              isAnyRepoInUse ? 'opacity-50 cursor-not-allowed' : ''
            }`}
            onClick={refreshRepos}
            disabled={isAnyRepoInUse}
          >
            Refresh Repositories
          </button>
        </div>

        {showNotification && (
          <div
            className={`${
              notification.errorType === null
                ? 'bg-blue-100 border-blue-500 text-blue-700'
                : 'bg-red-100 border-red-500 text-red-700'
            } border-l-4 p-4 mb-4 relative`}
            role='alert'
          >
            <button
              className='absolute right-2 top-2 px-4 py-2 text-sm border-none font-medium leading-5 text-gray-700 transition-colors duration-150 border border-gray-300 rounded-lg active:bg-gray-50 focus:outline-none focus:shadow-outline-gray'
              onClick={dismissError}
            >
              Dismiss
            </button>
            <p className='font-bold'>{notification.repoName}</p>
            <div dangerouslySetInnerHTML={{ __html: notification.message }} />
          </div>
        )}
        {repositories.length > 0 && (
          <table className='table-auto w-full border-collapse border-t border-b'>
            <thead>
              <tr>
                <th className='text-left px-4 py-2'>Repository Name</th>
                <th className='text-left px-4 py-2 w-48'>Status</th>
                <th className='text-left px-4 py-2'>Actions</th>
              </tr>
            </thead>
            <tbody>
              {repositories.map((repo, index) => (
                <tr key={repo.id} className='border-t'>
                  <td className='px-4 py-2'>
                    <a
                      href={repo.url}
                      target='_blank'
                      rel='noopener noreferrer'
                      className='text-blue-500 hover:text-blue-800'
                    >
                      {repo.name}
                    </a>
                  </td>
                  <td className='px-4 py-2'>
                    <span
                      className={`inline-block rounded-full px-3 py-1 text-sm font-semibold text-white ${
                        repo.inUse === 'Active'
                          ? 'bg-green-500'
                          : repo.inUse === 'Initialising...'
                          ? 'bg-yellow-500'
                          : 'bg-red-500'
                      }`}
                    >
                      {repo.inUse}
                    </span>
                  </td>
                  <td className='px-4 py-2 relative'>
                    <div
                      className='inline-block text-left'
                      ref={el => (dropdownRefs.current[index] = el)}
                    >
                      <button
                        className={`inline-flex justify-center w-full rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 ${
                          repo.inUse === 'Initialising...' ||
                          repo.inUse === 'Turning Off...' ||
                          isAnyRepoInUse
                            ? 'opacity-50 cursor-not-allowed'
                            : ''
                        }`}
                        onClick={() => toggleDropdown(index)}
                        disabled={repo.inUse === 'Initialising...' || repo.inUse === 'Turning Off...' || isAnyRepoInUse}
                      >
                        Actions
                        <svg
                          className='-mr-1 ml-2 h-5 w-5'
                          xmlns='http://www.w3.org/2000/svg'
                          viewBox='0 0 20 20'
                          fill='currentColor'
                          aria-hidden='true'
                        >
                          <path
                            fillRule='evenodd'
                            d='M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 011.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z'
                            clipRule='evenodd'
                          />
                        </svg>
                      </button>
                      {openDropdown === index &&
                        repo.inUse !== 'Initialising...' &&
                        repo.inUse !== 'Turning Off...' && (
                          <div
                            className='origin-top-right absolute left-0 mt-2 w-56 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 focus:outline-none z-10'
                            role='menu'
                            aria-orientation='vertical'
                            aria-labelledby='menu-button'
                            tabIndex='-1'
                          >
                            <div className='py-1' role='none'>
                              {repo.inUse !== 'Inactive' && (
                                <>
                                  <a
                                    href='#'
                                    className='text-gray-700 block px-4 py-2 text-sm hover:bg-gray-100'
                                    role='menuitem'
                                    tabIndex='-1'
                                    onClick={() =>
                                      setMonitoringStatus(repo.id, false)
                                    }
                                  >
                                    Turn off
                                  </a>
                                </>
                              )}
                              {repo.inUse === 'Inactive' && (
                                <>
                                  <a
                                    href='#'
                                    className='text-gray-700 block px-4 py-2 text-sm hover:bg-gray-100'
                                    role='menuitem'
                                    tabIndex='-1'
                                    onClick={() =>
                                      setMonitoringStatus(repo.id, true)
                                    }
                                  >
                                    Turn on
                                  </a>
                                </>
                              )}
                            </div>
                          </div>
                        )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {repositories.length === 0 && (
          <div className='mt-4 p-4 bg-gray-100 border border-gray-300 rounded'>
            <p className='text-gray-700'>
              No repositories found. To get started, install the GitHub app and
              allow access to your repositories. You can install it&nbsp;
              <a
                href='https://github.com/apps/co-op-translator'
                target='_blank'
                rel='noopener noreferrer'
                className='text-blue-500 underline'
              >
                here.
              </a>
              
            </p>
            <p className='text-gray-700'>
              If you have already installed the app but cannot see any
              repositories here, make sure you have allowed access to your
              repos, and then refresh again.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default Dashboard;

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + '=') {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
