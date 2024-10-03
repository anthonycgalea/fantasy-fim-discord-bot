import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import api from '../api'; // Adjust the import path based on your project structure
import { Tabs, Tab } from 'react-bootstrap'; // Ensure you have react-bootstrap installed
import Rankings from './Rankings';
import LeagueDrafts from './LeagueDrafts'
import Waivers from './Waivers';
import FreeAgentTeams from './FreeAgentTeams';
import Rosters from './Rosters';
import ScoresLineups from './ScoresLineups';

const FantasyLeague = () => {

    const { leagueId } = useParams(); // Get the leagueId from the URL
    const [league, setLeague] = useState([]);

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

    return (
      <div className="container mt-5">
        <h1 className="mb-4 text-center">{league.league_name}</h1>
        <Tabs defaultActiveKey="rankings" id="fantasy-league-tabs">
          <Tab eventKey="rankings" title="Rankings">
            {
                <div>
                <Rankings leagueId={leagueId}></Rankings>
                </div>
            }
          </Tab>
          <Tab eventKey="scores" title="Scores/Lineups">
            {
              <div>
                <ScoresLineups leagueId={leagueId}></ScoresLineups>
              </div>
            }
          </Tab>
          <Tab eventKey="rosters" title="Rosters">
          {
              <div>
                <Rosters leagueId={leagueId}></Rosters>
              </div>
            }
          </Tab>
          <Tab eventKey="availableTeams" title="Available Teams">
          {
              <div>
                <FreeAgentTeams leagueId={leagueId}></FreeAgentTeams>
              </div>
            }
          </Tab>
          <Tab eventKey="waivers" title="Waivers">
          {
              <div>
                <Waivers leagueId={leagueId}></Waivers>
              </div>
            }
          </Tab>
          <Tab eventKey="drafts" title="Drafts">
            {
              <div>
                <LeagueDrafts leagueId={leagueId}></LeagueDrafts>
              </div>
            }
          </Tab>
        </Tabs>
      </div>
    );
  };

export default FantasyLeague;