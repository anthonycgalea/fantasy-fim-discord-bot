import React, { useEffect, useState } from 'react';
import api from '../api'; // Adjust the import path based on your project structure
import "./Waivers.css";

const Waivers = ({leagueId}) => {
    const [league, setLeague] = useState(null)
    const [waiverTeams, setWaiverTeams] = useState([]);
    const [waiverPriority, setWaiverPriority] = useState([]);
  const [activeTab, setActiveTab] = useState('waiverTeams'); // State for active tab
  const [selectedWeeks, setSelectedWeeks] = useState([1, 2, 3, 4, 5]); // Initially include all weeks


  useEffect(() => {
    const fetchDraftData = async () => {
      try {
        const [leaguesResponse, waiverResponse, waiverPriorityResponse] = await Promise.all([
          api.get(`/leagues/${leagueId}`),
          api.get(`/leagues/${leagueId}/teamsOnWaivers`),
          api.get(`/leagues/${leagueId}/waiverPriority`)
        ]);
        setLeague(leaguesResponse.data); 
        setWaiverTeams(waiverResponse.data);
        setWaiverPriority(waiverPriorityResponse.data);

      } catch (error) {
        console.error('Error fetching draft data:', error);
      }
    };
  
    fetchDraftData();
  }, [leagueId]);

  const toggleWeekSelection = (week) => {
    setSelectedWeeks((prevSelectedWeeks) =>
      prevSelectedWeeks.includes(week)
        ? prevSelectedWeeks.filter((w) => w !== week) // Remove if already selected
        : [...prevSelectedWeeks, week] // Add if not selected
    );
  };

  const renderWaiverTeams = () => {
    const weeks = [1, 2, 3, 4, 5]; // Define the weeks array here
  
    // Create a data structure to hold the events for each team by week, including year_end_epa
    const teamEventsByWeek = waiverTeams.map((team) => {
      const events = weeks.map((week) => {
        const event = team.events.find((e) => e.week === week);
        return event ? event.event_key : ''; // Set event key or empty string
      });
      return { 
        teamNumber: team.team_number, 
        teamName: team.name,
        events, 
        yearEndEpa: team.year_end_epa // Include year_end_epa here
      };
    });
  
    // Filter teams based on selected weeks
    const filteredTeams = teamEventsByWeek.filter(({ events }) =>
      selectedWeeks.some((week) => events[week - 1] !== '') // Check if any selected week has an event
    );
    return (
      <table className="table table-bordered">
        <thead className='table-secondary'>
          <tr>
            <th rowspan="3" class="align-middle">Team #</th>
            <th rowspan="3" class="align-middle">Team Name</th>
            <th colspan="5">Week</th>
          </tr>
          <tr>
            <th>1</th>
            <th>2</th>
            <th>3</th>
            <th>4</th>
            <th>5</th>
          </tr>
          <tr>
            {weeks.map((week) => (
              <th key={week} className="equal-width">
              <div className="form-check form-switch d-flex justify-content-center align-items-center">
                <input
                  type="checkbox"
                  className="form-check-input"
                  checked={selectedWeeks.includes(week)}
                  onChange={() => toggleWeekSelection(week)}
                />
              </div>
            </th>
            
            ))}
          </tr>
        </thead>
        <tbody>
          {filteredTeams.map(({ teamNumber, teamName, events, yearEndEpa }) => (
            <tr key={teamNumber}>
              <td>{teamNumber}</td>
              <td>{teamName}</td>
              {events.map((event, index) => (
                <td key={index}>{event}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    );
  };

  const renderWaiverOrder = () => {
    return (
      <table className="table table-hover">
        <thead className='table-secondary'>
          <tr>
            <th>Priority</th>
            <th>Fantasy Team Name</th>
          </tr>
        </thead>
        <tbody>
          {waiverPriority.map(({ fantasy_team_id, fantasy_team_name, priority }) => (
            <tr key={fantasy_team_id} title={`Priority: ${priority}`}>
              <td>{priority}</td>
              <td>{fantasy_team_name}</td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  };
  

  return (
    <div className="container mt-5">
      <div className="row">
      {league ? ( // Check if league is loaded
        <h2 className="text-center">Waivers for {league ? league.league_name : 'Loading...'}</h2>
      ) : (
        <h2 className="text-center">Loading Waivers...</h2> // Loading message if draft is not yet available
      )}
    </div>
    <ul className="nav nav-tabs">
      <li className="nav-item flex-fill">
        <button
          className={`nav-link ${activeTab === 'waiverTeams' ? 'active' : ''}`}
          onClick={() => setActiveTab('waiverTeams')}
        >
          Teams on Waivers
        </button>
      </li>
      <li className="nav-item flex-fill">
        <button
          className={`nav-link ${activeTab === 'waiverOrder' ? 'active' : ''}`}
          onClick={() => setActiveTab('waiverOrder')}
        >
          Waiver Priority
        </button>
      </li>
    </ul>
      {activeTab === 'waiverTeams' && (
        <div className="mt-3">
          <div className="row">
            {renderWaiverTeams()}
          </div>
        </div>
      )}
      {activeTab === 'waiverOrder' && (
        <div className="mt-3">
          <div className="row">
            {renderWaiverOrder()}
          </div>
        </div>
      )}
    </div>
  );
};

export default Waivers;
