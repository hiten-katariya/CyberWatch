import React, { useState, useEffect } from 'react';
import { Search, X } from 'lucide-react';

export default function SearchInput({ value, onChange, placeholder = "Search IP, domain, hash, alert ID..." }) {
  const [term, setTerm] = useState(value || '');

  useEffect(() => {
    const handler = setTimeout(() => {
      onChange(term);
    }, 250);
    return () => clearTimeout(handler);
  }, [term, onChange]);

  return (
    <div className="search-box">
      <Search size={14} color="var(--text-secondary)" />
      <input 
        type="text" 
        value={term}
        onChange={e => setTerm(e.target.value)}
        placeholder={placeholder}
        className="search-input mono"
      />
      {term && (
        <button onClick={() => setTerm('')} className="search-clear-btn">
          <X size={12} />
        </button>
      )}
    </div>
  );
}
