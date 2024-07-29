import githubLogo from './assets/github-white.svg';
import logo from './assets/logo.png';

function Login() {
  return (
    <div className='h-screen flex flex-col'>
      <header className='bg-blue-600 text-white p-4 grid grid-cols-[auto_1fr] items-center gap-4'>
        <div className='bg-white p-1 rounded'>
          <a href='https://msft-icl-cooperator.netlify.app/'>
            <img src={logo} alt='Logo' className='w-12 h-12' />
          </a>
        </div>
        <h1 className='text-xl font-bold'>
          Co-Operator: Automated Repository Management
        </h1>
      </header>

      <div className='flex-grow p-8 text-center flex justify-center items-center'>
        <div className='flex flex-col items-center justify-center'>
          <button
            className='flex items-center px-5 py-3 text-lg bg-gray-800 text-white rounded-md cursor-pointer mb-5 min-w-[240px] hover:bg-gray-700'
            onClick={() => (window.location.href = '/auth/github/login')}
          >
            <img src={githubLogo} alt='GitHub logo' className='w-5 h-5 mr-2' />
            <span className='flex-1'>Sign in with GitHub</span>
          </button>
          {/* Additional buttons or content can be added here if needed */}
        </div>
      </div>
    </div>
  );
}

export default Login;
