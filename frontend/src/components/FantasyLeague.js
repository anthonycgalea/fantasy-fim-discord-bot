import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import api from '../api'; // Adjust the import path based on your project structure
import Rankings from './Rankings';
import LeagueDrafts from './LeagueDrafts'
import Waivers from './Waivers';
import FreeAgentTeams from './FreeAgentTeams';
import ScoresLineups from './ScoresLineups';
import RosterWeeks from './RosterWeeks';

const FantasyLeague = () => {

    const { leagueId } = useParams(); // Get the leagueId from the URL
    const [league, setLeague] = useState([]);
    const [activeTab, setActiveTab] = useState('rankings');

    useEffect(() => {
        const fetchLeague= async () => {
          try {
            const response = await api.get(`/leagues/${leagueId}`); // Adjust the endpoint if necessary
            console.log(response.data); // Log the response for debugging
            setLeague(response.data);
          } catch (error) {
            console.error('Error fetching league:', error);
          }
        };
        fetchLeague();
    }, [leagueId]);

    useEffect(() => {
      if (league?.is_fim !== undefined) {
          setActiveTab(league.is_fim ? 'rankings' : 'drafts');
      }
  }, [league]);

    return (
      <div className="container mt-5">
  <div className="row">
    <h1 className="mb-4 text-center">{league.league_name}</h1>
  </div>
  <ul className="nav nav-tabs">
    {/* Conditionally render tabs based on league.is_fim */}
    {!league?.is_fim && (
      <li className="nav-item flex-fill">
        <button
          className={`nav-link ${activeTab === 'drafts' ? 'active' : ''}`}
          onClick={() => setActiveTab('drafts')}
        >
          Drafts
        </button>
      </li>
    )}
    <li className="nav-item flex-fill">
      <button
        className={`nav-link ${activeTab === 'rankings' ? 'active' : ''}`}
        onClick={() => setActiveTab('rankings')}
      >
        Rankings
      </button>
    </li>
    {league?.is_fim && (
      <>
        <li className="nav-item flex-fill">
          <button
            className={`nav-link ${activeTab === 'scores' ? 'active' : ''}`}
            onClick={() => setActiveTab('scores')}
          >
            Scores/Lineups
          </button>
        </li>
        <li className="nav-item flex-fill">
          <button
            className={`nav-link ${activeTab === 'rosters' ? 'active' : ''}`}
            onClick={() => setActiveTab('rosters')}
          >
            Rosters
          </button>
        </li>
        <li className="nav-item flex-fill">
          <button
            className={`nav-link ${activeTab === 'availableTeams' ? 'active' : ''}`}
            onClick={() => setActiveTab('availableTeams')}
          >
            Available Teams
          </button>
        </li>
        <li className="nav-item flex-fill">
          <button
            className={`nav-link ${activeTab === 'waivers' ? 'active' : ''}`}
            onClick={() => setActiveTab('waivers')}
          >
            Waivers
          </button>
        </li>
        <li className="nav-item flex-fill">
          <button
            className={`nav-link ${activeTab === 'drafts' ? 'active' : ''}`}
            onClick={() => setActiveTab('drafts')}
          >
            Drafts
          </button>
        </li>
      </>
    )}
  </ul>

  {/* Render the content for the active tab */}
  {activeTab === 'drafts' && (
    <div className="mt-3">
      <LeagueDrafts leagueId={leagueId}></LeagueDrafts>
    </div>
  )}
  {activeTab === 'rankings' && (
    <div className="mt-3">
      <Rankings leagueId={leagueId}></Rankings>
    </div>
  )}
  {activeTab === 'scores' && (
    <div className="mt-3">
      <ScoresLineups leagueId={leagueId}></ScoresLineups>
    </div>
  )}
  {activeTab === 'rosters' && (
    <div className="mt-3">
      <RosterWeeks leagueId={leagueId}></RosterWeeks>
    </div>
  )}
  {activeTab === 'availableTeams' && (
    <div className="mt-3">
      <FreeAgentTeams leagueId={leagueId}></FreeAgentTeams>
    </div>
  )}
  {activeTab === 'waivers' && (
    <div className="mt-3">
      <Waivers leagueId={leagueId}></Waivers>
    </div>
  )}
</div>
    );
  };

export default FantasyLeague;