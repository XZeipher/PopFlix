import React, { useState, useEffect, useContext, createContext } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = createContext();

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('token'));

  useEffect(() => {
    if (token) {
      // Verify token and get user profile
      fetchProfile();
    } else {
      setLoading(false);
    }
  }, [token]);

  const fetchProfile = async () => {
    try {
      const response = await axios.get(`${API}/profile`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUser(response.data);
    } catch (error) {
      // Token invalid, clear it
      localStorage.removeItem('token');
      setToken(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (googleToken) => {
    try {
      const response = await axios.post(`${API}/auth/google`, {
        token: googleToken
      });
      
      const { token: jwtToken, user: userData } = response.data;
      localStorage.setItem('token', jwtToken);
      setToken(jwtToken);
      setUser(userData);
      
      return true;
    } catch (error) {
      console.error('Login failed:', error);
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, token }}>
      {children}
    </AuthContext.Provider>
  );
};

const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

// Components
const Navigation = () => {
  const { user, logout } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [showResults, setShowResults] = useState(false);

  const handleSearch = async (query) => {
    if (!query.trim()) {
      setSearchResults([]);
      setShowResults(false);
      return;
    }

    try {
      const response = await axios.get(`${API}/search?q=${encodeURIComponent(query)}`);
      setSearchResults(response.data.results);
      setShowResults(true);
    } catch (error) {
      console.error('Search failed:', error);
    }
  };

  const handleGoogleLogin = () => {
    // For demo, simulate Google OAuth
    // In production, use actual Google OAuth library
    const mockGoogleToken = 'demo-token';
    // login(mockGoogleToken);
    alert('Google login integration needed - using mock for demo');
  };

  return (
    <nav className="bg-black/95 backdrop-blur-md border-b border-blue-500/20 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center">
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
              PopFlix
            </h1>
          </div>

          {/* Search Bar */}
          <div className="flex-1 max-w-md mx-8 relative">
            <div className="relative">
              <input
                type="text"
                placeholder="Search movies, shows, anime..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  handleSearch(e.target.value);
                }}
                className="w-full bg-gray-900/50 border border-gray-600/50 rounded-full py-2 px-4 pl-10 text-white placeholder-gray-400 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
              />
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
            </div>

            {/* Search Results */}
            {showResults && searchResults.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-gray-900/95 backdrop-blur-md border border-gray-600/50 rounded-lg max-h-96 overflow-y-auto z-50">
                {searchResults.slice(0, 5).map((result, index) => (
                  <div
                    key={index}
                    className="flex items-center p-3 hover:bg-gray-800/50 cursor-pointer border-b border-gray-700/50 last:border-b-0"
                    onClick={() => {
                      setShowResults(false);
                      setSearchQuery('');
                    }}
                  >
                    <img
                      src={`https://image.tmdb.org/t/p/w92${result.data.poster_path || result.data.poster_path}`}
                      alt={result.data.title || result.data.name}
                      className="w-12 h-16 object-cover rounded"
                      onError={(e) => { e.target.src = '/placeholder-poster.jpg' }}
                    />
                    <div className="ml-3">
                      <p className="text-white font-medium">{result.data.title || result.data.name}</p>
                      <p className="text-gray-400 text-sm capitalize">{result.type}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* User Menu */}
          <div className="flex items-center space-x-4">
            {user ? (
              <div className="flex items-center space-x-3">
                {user.is_premium && (
                  <span className="bg-gradient-to-r from-yellow-400 to-yellow-600 text-black px-2 py-1 rounded-full text-xs font-bold">
                    ⭐ PREMIUM
                  </span>
                )}
                <img
                  src={user.picture || '/default-avatar.jpg'}
                  alt={user.name}
                  className="w-8 h-8 rounded-full ring-2 ring-blue-500/50"
                />
                <span className="text-white hidden sm:block">{user.name}</span>
                <button
                  onClick={logout}
                  className="text-gray-400 hover:text-white transition-colors"
                >
                  Logout
                </button>
              </div>
            ) : (
              <button
                onClick={handleGoogleLogin}
                className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white px-4 py-2 rounded-full font-medium transition-all duration-200 transform hover:scale-105"
              >
                Login with Google
              </button>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};

const Hero = () => {
  return (
    <div className="relative h-screen bg-gradient-to-br from-black via-gray-900 to-blue-900 flex items-center justify-center overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-900/20 to-purple-900/20 animate-pulse"></div>
      
      <div className="relative z-10 text-center max-w-4xl mx-auto px-4">
        <h1 className="text-7xl md:text-9xl font-bold bg-gradient-to-r from-blue-400 via-purple-500 to-pink-500 bg-clip-text text-transparent mb-6 animate-pulse">
          PopFlix
        </h1>
        <p className="text-xl md:text-2xl text-gray-300 mb-8 max-w-2xl mx-auto">
          The future of streaming is here. Movies, shows, anime, and premium content - all in one futuristic platform.
        </p>
        
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <button className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white px-8 py-4 rounded-full font-bold text-lg transition-all duration-300 transform hover:scale-105 hover:shadow-2xl hover:shadow-blue-500/25">
            Start Watching Free
          </button>
          <button className="border-2 border-blue-500 text-blue-400 hover:bg-blue-500 hover:text-white px-8 py-4 rounded-full font-bold text-lg transition-all duration-300 transform hover:scale-105">
            Get Premium ⭐
          </button>
        </div>

        {/* Features */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16">
          <div className="bg-gray-900/50 backdrop-blur-md border border-gray-700/50 rounded-xl p-6 text-center hover:border-blue-500/50 transition-colors">
            <div className="text-4xl mb-4">🎬</div>
            <h3 className="text-xl font-bold text-white mb-2">Unlimited Movies</h3>
            <p className="text-gray-400">Latest blockbusters and classics</p>
          </div>
          <div className="bg-gray-900/50 backdrop-blur-md border border-gray-700/50 rounded-xl p-6 text-center hover:border-purple-500/50 transition-colors">
            <div className="text-4xl mb-4">📺</div>
            <h3 className="text-xl font-bold text-white mb-2">TV Shows & Anime</h3>
            <p className="text-gray-400">Binge-watch your favorites</p>
          </div>
          <div className="bg-gray-900/50 backdrop-blur-md border border-gray-700/50 rounded-xl p-6 text-center hover:border-pink-500/50 transition-colors">
            <div className="text-4xl mb-4">⭐</div>
            <h3 className="text-xl font-bold text-white mb-2">Premium Content</h3>
            <p className="text-gray-400">Exclusive 18+ content & HD quality</p>
          </div>
        </div>
      </div>
    </div>
  );
};

const ContentSection = ({ title, data, type }) => {
  const { user, token } = useAuth();

  const playContent = async (item) => {
    if (item.adult && !user?.is_premium) {
      alert('Premium membership required for adult content');
      return;
    }

    try {
      const tmdbId = item.tmdb_id;
      const response = await axios.get(`${API}/stream/${type}/${tmdbId}`);
      const streamData = response.data;

      // Add to watch history if user is logged in
      if (user && token) {
        await axios.post(`${API}/watchhistory`, {
          content_type: type,
          tmdb_id: tmdbId,
          title: item.title || item.name,
          poster_path: item.poster_path
        }, {
          headers: { Authorization: `Bearer ${token}` }
        });
      }

      // Open stream in new window
      window.open(streamData.embed_url, '_blank');
    } catch (error) {
      console.error('Failed to get stream:', error);
      alert('Failed to load stream. Please try again.');
    }
  };

  const addToFavorites = async (item) => {
    if (!user || !token) {
      alert('Please login to add favorites');
      return;
    }

    try {
      await axios.post(`${API}/favorites`, {
        content_type: type,
        tmdb_id: item.tmdb_id,
        title: item.title || item.name,
        poster_path: item.poster_path
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      alert('Added to favorites!');
    } catch (error) {
      console.error('Failed to add favorite:', error);
      if (error.response?.data?.message === "Already in favorites") {
        alert('Already in favorites!');
      }
    }
  };

  return (
    <section className="py-12 bg-black">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <h2 className="text-3xl font-bold text-white mb-8 bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
          {title}
        </h2>
        
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {data.map((item, index) => (
            <div
              key={index}
              className="group relative bg-gray-900/50 rounded-lg overflow-hidden hover:scale-105 transition-all duration-300 hover:shadow-xl hover:shadow-blue-500/25"
            >
              <div className="aspect-[2/3] relative">
                <img
                  src={`https://image.tmdb.org/t/p/w500${item.poster_path}`}
                  alt={item.title || item.name}
                  className="w-full h-full object-cover"
                  onError={(e) => { e.target.src = '/placeholder-poster.jpg' }}
                />
                
                {item.adult && (
                  <div className="absolute top-2 right-2 bg-red-600 text-white text-xs px-2 py-1 rounded-full font-bold">
                    18+
                  </div>
                )}

                {/* Hover overlay */}
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                  <div className="absolute bottom-0 left-0 right-0 p-4">
                    <h3 className="text-white font-bold text-sm mb-2 line-clamp-2">
                      {item.title || item.name}
                    </h3>
                    
                    <div className="flex space-x-2">
                      <button
                        onClick={() => playContent(item)}
                        className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded-full text-xs font-medium transition-colors"
                      >
                        ▶️ Play
                      </button>
                      <button
                        onClick={() => addToFavorites(item)}
                        className="bg-gray-700 hover:bg-gray-600 text-white px-3 py-1 rounded-full text-xs font-medium transition-colors"
                      >
                        ❤️
                      </button>
                    </div>

                    {item.vote_average && (
                      <div className="flex items-center mt-2">
                        <span className="text-yellow-400 text-xs">⭐</span>
                        <span className="text-white text-xs ml-1">{item.vote_average.toFixed(1)}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

const PremiumSection = () => {
  const { user, token } = useAuth();
  const [loading, setLoading] = useState(false);

  const upgradeToPremium = async () => {
    if (!user || !token) {
      alert('Please login first');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${API}/payments/create-checkout`, {
        package_id: 'premium_monthly',
        origin_url: window.location.origin
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      // Redirect to Stripe checkout
      window.location.href = response.data.checkout_url;
    } catch (error) {
      console.error('Payment failed:', error);
      alert('Payment initiation failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (user?.is_premium) {
    return (
      <section className="py-16 bg-gradient-to-br from-yellow-900/20 to-yellow-700/20">
        <div className="max-w-4xl mx-auto text-center px-4">
          <h2 className="text-4xl font-bold text-yellow-400 mb-4">⭐ You're Premium!</h2>
          <p className="text-xl text-gray-300 mb-8">
            Enjoy unlimited access to all content, HD streaming, and exclusive features.
          </p>
          <div className="bg-gradient-to-r from-yellow-600 to-yellow-800 text-black p-6 rounded-xl">
            <p className="font-bold">Premium Benefits Active:</p>
            <ul className="mt-2 space-y-1 text-sm">
              <li>✓ No advertisements</li>
              <li>✓ 18+ premium content</li>
              <li>✓ HD quality streaming</li>
              <li>✓ Download for offline viewing</li>
              <li>✓ Comment on content</li>
            </ul>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="py-16 bg-gradient-to-br from-blue-900/20 to-purple-900/20">
      <div className="max-w-4xl mx-auto text-center px-4">
        <h2 className="text-4xl font-bold text-white mb-4">Upgrade to Premium</h2>
        <p className="text-xl text-gray-300 mb-8">
          Unlock the full PopFlix experience with premium features
        </p>

        <div className="bg-gradient-to-br from-gray-900/50 to-gray-800/50 backdrop-blur-md border border-gray-700/50 rounded-xl p-8 mb-8">
          <div className="text-center mb-6">
            <div className="text-5xl font-bold text-white mb-2">₹200</div>
            <div className="text-gray-400">per month</div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <div className="space-y-3">
              <div className="flex items-center text-green-400">
                <span className="mr-3">✓</span>
                <span>No advertisements</span>
              </div>
              <div className="flex items-center text-green-400">
                <span className="mr-3">✓</span>
                <span>18+ premium content</span>
              </div>
              <div className="flex items-center text-green-400">
                <span className="mr-3">✓</span>
                <span>HD quality streaming</span>
              </div>
            </div>
            <div className="space-y-3">
              <div className="flex items-center text-green-400">
                <span className="mr-3">✓</span>
                <span>Download for offline viewing</span>
              </div>
              <div className="flex items-center text-green-400">
                <span className="mr-3">✓</span>
                <span>Comment on content</span>
              </div>
              <div className="flex items-center text-green-400">
                <span className="mr-3">✓</span>
                <span>Priority customer support</span>
              </div>
            </div>
          </div>

          <button
            onClick={upgradeToPremium}
            disabled={loading}
            className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white px-8 py-4 rounded-full font-bold text-lg transition-all duration-300 transform hover:scale-105 disabled:opacity-50"
          >
            {loading ? 'Processing...' : 'Upgrade Now ⭐'}
          </button>
        </div>
      </div>
    </section>
  );
};

const Footer = () => {
  return (
    <footer className="bg-black border-t border-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col md:flex-row justify-between items-center">
          <div className="mb-4 md:mb-0">
            <h3 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
              PopFlix
            </h3>
            <p className="text-gray-400 text-sm mt-1">The future of streaming</p>
          </div>
          
          <div className="flex space-x-6">
            <a href="#" className="text-gray-400 hover:text-blue-400 transition-colors hover:glow">Terms</a>
            <a href="#" className="text-gray-400 hover:text-blue-400 transition-colors hover:glow">Privacy</a>
            <a href="#" className="text-gray-400 hover:text-blue-400 transition-colors hover:glow">Contact</a>
          </div>
        </div>
        
        <div className="mt-6 pt-6 border-t border-gray-800 text-center text-gray-500 text-sm">
          <p>&copy; 2024 PopFlix. All rights reserved. Built for the future of entertainment.</p>
        </div>
      </div>
    </footer>
  );
};

const App = () => {
  const [popularMovies, setPopularMovies] = useState([]);
  const [popularTV, setPopularTV] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchContent = async () => {
      try {
        const [moviesResponse, tvResponse] = await Promise.all([
          axios.get(`${API}/movies/popular`),
          axios.get(`${API}/tv/popular`)
        ]);

        setPopularMovies(moviesResponse.data.results);
        setPopularTV(tvResponse.data.results);
      } catch (error) {
        console.error('Failed to fetch content:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchContent();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500 mb-4"></div>
          <p className="text-white text-xl">Loading PopFlix...</p>
        </div>
      </div>
    );
  }

  return (
    <AuthProvider>
      <div className="min-h-screen bg-black">
        <Navigation />
        <Hero />
        <ContentSection title="🔥 Popular Movies" data={popularMovies} type="movie" />
        <ContentSection title="📺 Popular TV Shows" data={popularTV} type="tv" />
        <PremiumSection />
        <Footer />
      </div>
    </AuthProvider>
  );
};

export default App;