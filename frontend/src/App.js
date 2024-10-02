// src/App.js
import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import Navbar from './components/Navbar';
import Rankings from './components/Rankings';
import Leagues from './components/Leagues';
import LeagueDrafts from './components/LeagueDrafts';
import Drafts from './components/Drafts'
import 'bootstrap/dist/css/bootstrap.min.css';

function App() {
  return (
    <Router>
      <Navbar /> 
      <Routes>
        <Route path="/" element={<Leagues />} />
        <Route path="/leagues/:leagueId/rankings" element={<Rankings />} />
        <Route path="/leagues/:leagueId/drafts" element={<LeagueDrafts />} />
        <Route path="/drafts/:draftId" element={<Drafts />} />
        {/* Add more routes as needed */}
      </Routes>
    </Router>
  );
}

export default App;
