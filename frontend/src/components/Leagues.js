// src/components/Leagues.js
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api'; // Adjust this path based on your project structure
import { Tabs, Tab } from 'react-bootstrap'; // Ensure you have react-bootstrap installed
import Table from 'react-bootstrap/Table';

const Leagues = () => {
  const [leagues, setLeagues] = useState([]);

  useEffect(() => {
    const fetchLeagues = async () => {
      try {
        const response = await api.get('/leagues'); // Fetch leagues from the API
        const leaguesData = response.data;
        const backfilledLeagues = backfillLeagues(leaguesData); // Backfill leagues data
        setLeagues(backfilledLeagues);
      } catch (error) {
        console.error('Error fetching leagues:', error);
      }
    };

    fetchLeagues();
  }, []);

  // Function to backfill league data (modify this based on your backfill needs)
  const backfillLeagues = (leaguesData) => {
    return leaguesData.map(league => {
      return {
        ...league,
        team_limit: league.team_limit || 0, // Ensure team_limit has a default value
        team_starts: league.team_starts || 0, // Ensure team_starts has a default value
        year: league.year || new Date().getFullYear(), // Default to current year if missing
        // Add any other backfill logic here
      };
    });
  };

  // Filter leagues for FiM leagues, offseason drafts, and in-season drafts
  const fimLeagues = leagues.filter(league => league.is_fim);
  const offseasonDrafts = leagues.filter(league => league.offseason);
  const inSeasonDrafts = leagues.filter(league => !league.offseason && !league.is_fim);

  return (
    <div className="container mt-5">
      <h1 className="mb-4 text-center">Active Leagues</h1>
      <Tabs defaultActiveKey="fim" id="leagues-tabs">
        <Tab eventKey="fim" title="FiM Leagues">
          {fimLeagues.length > 0 ? (
            <Table bordered hover>
              <thead>
                <tr>
                  <th>League ID</th>
                  <th>League Name</th>
                  <th>Fantasy Teams</th>
                  <th>Starts per Week</th>
                  <th>Team Size</th>
                  <th>Year</th>
                </tr>
              </thead>
              <tbody>
                {fimLeagues.map(league => (
                  <tr key={league.league_id}>
                    <td>{league.league_id}</td>
                    <td>
                      <Link to={`/leagues/${league.league_id}`}>{league.league_name}</Link>
                    </td>
                    <td>{league.team_limit}</td>
                    <td>{league.team_starts}</td>
                    <td>{league.team_size_limit}</td>
                    <td>{league.year}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          ) : (
            <div>No FiM leagues available.</div> // Message when no leagues are available
          )}
        </Tab>

        <Tab eventKey="offseason" title="Offseason Leagues">
          {offseasonDrafts.length > 0 ? (
            <Table striped bordered hover>
              <thead>
                <tr>
                  <th>League ID</th>
                  <th>League Name</th>
                  <th>Year</th>
                  <th>Teams</th>
                </tr>
              </thead>
              <tbody>
                {offseasonDrafts.map(league => (
                  <tr key={league.league_id}>
                    <td>{league.league_id}</td>
                    <td>
                      <Link to={`/leagues/${league.league_id}`}>{league.league_name}</Link>
                    </td>
                    <td>{league.year}</td>
                    <td>{league.team_limit}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          ) : (
            <div>No Offseason leagues available.</div> // Message when no leagues are available
          )}
        </Tab>

        <Tab eventKey="inseason" title="In-Season Drafts">
          {inSeasonDrafts.length > 0 ? (
            <Table striped bordered hover>
              <thead>
                <tr>
                  <th>League ID</th>
                  <th>League Name</th>
                  <th>Year</th>
                  <th>Teams</th>
                </tr>
              </thead>
              <tbody>
                {inSeasonDrafts.map(league => (
                  <tr key={league.league_id}>
                    <td>{league.league_id}</td>
                    <td>
                      <Link to={`/leagues/${league.league_id}`}>{league.league_name}</Link>
                    </td>
                    <td>{league.year}</td>
                    <td>{league.team_limit}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          ) : (
            <div>No In-Season leagues available.</div> // Message when no leagues are available
          )}
        </Tab>
      </Tabs>
    </div>
  );
};

export default Leagues;
