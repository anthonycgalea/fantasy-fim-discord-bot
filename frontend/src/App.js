// src/App.js
import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import Navbar from './components/Navbar';
import Leagues from './components/Leagues';
import Drafts from './components/Drafts'
import FantasyLeague from './components/FantasyLeague';
import 'bootstrap/dist/css/bootstrap.min.css';

function App() {
  return (
    <Router>
      <Navbar /> 
      <Routes>
        <Route path="/" element={<Leagues />} />
        <Route path="/leagues/:leagueId" element={<FantasyLeague />} />
        <Route path="/drafts/:draftId" element={<Drafts />} />
        {/* Add more routes as needed */}
      </Routes>
    </Router>
  );
}

export default App;
