import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authAPI, extractionAPI } from '../services/api';
import './Dashboard.css';

function Dashboard({ setIsAuthenticated }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [extractions, setExtractions] = useState([]);
  const [selectedExtraction, setSelectedExtraction] = useState(null);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    fetchExtractions();
  }, []);

  const fetchExtractions = async () => {
    try {
      const data = await extractionAPI.listExtractions();
      setExtractions(data.extractions);
    } catch (err) {
      console.error('Failed to fetch extractions:', err);
    }
  };

  const handleLogout = () => {
    authAPI.logout();
    setIsAuthenticated(false);
    navigate('/login');
  };

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setError('');
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file');
      return;
    }

    setUploading(true);
    setError('');

    try {
      const result = await extractionAPI.uploadFile(file);
      alert(`Successfully extracted ${result.clauses.length} clauses!`);
      setFile(null);
      await fetchExtractions();
      setSelectedExtraction(result);
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="dashboard">
      <header>
        <h1>Contract Clause Extractor</h1>
        <button onClick={handleLogout} className="logout-btn">Logout</button>
      </header>

      <div className="dashboard-content">
        <div className="upload-section">
          <h2>Upload Contract</h2>
          {error && <div className="error">{error}</div>}

          <div className="file-upload">
            <input
              type="file"
              accept=".pdf,.docx,.txt"
              onChange={handleFileChange}
              disabled={uploading}
            />
            {file && <p className="file-name">{file.name}</p>}
            <button
              onClick={handleUpload}
              disabled={!file || uploading}
              className="upload-btn"
            >
              {uploading ? 'Extracting...' : 'Extract Clauses'}
            </button>
          </div>
        </div>

        <div className="extractions-section">
          <h2>Recent Extractions</h2>
          <div className="extractions-list">
            {extractions.map((extraction) => (
              <div
                key={extraction.id}
                className="extraction-item"
                onClick={() => setSelectedExtraction(extraction)}
              >
                <h3>{extraction.filename}</h3>
                <p>Clauses: {extraction.clauses.length}</p>
                <p className="date">{new Date(extraction.created_at).toLocaleString()}</p>
              </div>
            ))}
          </div>
        </div>

        {selectedExtraction && (
          <div className="extraction-details">
            <div className="modal-overlay" onClick={() => setSelectedExtraction(null)}>
              <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                <button className="close-btn" onClick={() => setSelectedExtraction(null)}>×</button>
                <h2>{selectedExtraction.filename}</h2>
                <p>Status: <span className={`status ${selectedExtraction.status}`}>{selectedExtraction.status}</span></p>
                <p>Total Clauses: {selectedExtraction.clauses.length}</p>

                <div className="clauses-list">
                  {selectedExtraction.clauses.map((clause, index) => (
                    <div key={clause.id} className="clause-card">
                      <h4>{index + 1}. {clause.title}</h4>
                      <p className="clause-type">{clause.clause_type}</p>
                      <p className="clause-content">{clause.content}</p>
                      {clause.extra_data?.summary && (
                        <p className="clause-summary"><strong>Summary:</strong> {clause.extra_data.summary}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Dashboard;
