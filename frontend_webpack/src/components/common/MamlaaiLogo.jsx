import React from 'react';

const MamlaaiLogo = () => {
  return (
    <svg width="350" height="150" viewBox="0 0 350 150" xmlns="http://www.w3.org/2000/svg">
      {/* Background with rounded corners and border */}
      <rect x="0" y="0" width="350" height="150" fill="#ffffff" rx="12" ry="12" stroke="#0D47A1" strokeWidth="2" />
      
      {/* Ashoka Pillar Element */}
      <rect x="20" y="30" width="40" height="90" rx="5" ry="5" fill="#0D47A1" />
      <polygon points="20,30 40,10 60,30" fill="#0D47A1" />
      
      {/* Gavel Element representing the emblem of law */}
      <line x1="70" y1="80" x2="110" y2="80" stroke="#0D47A1" strokeWidth="6" strokeLinecap="round" />
      <rect x="100" y="70" width="20" height="15" fill="#0D47A1" />
      
      {/* Company Name Text */}
      <text x="140" y="60" fill="#0D47A1" fontSize="40" fontFamily="Arial, sans-serif" fontWeight="bold">
        MamlaAi
      </text>
      
      {/* Tagline Text */}
      <text x="140" y="90" fill="#0D47A1" fontSize="16" fontFamily="Arial, sans-serif">
        bringing law at your fingertips
      </text>
    </svg>
  );
};

export default MamlaaiLogo; 