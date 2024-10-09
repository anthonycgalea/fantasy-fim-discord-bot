import React, { useState, useEffect } from 'react';
import { Table, Form } from 'react-bootstrap';
import api from '../api'; // Adjust the import path
import Rosters from './Rosters'; // Import the Rosters component

const RosterWeeks = ({ leagueId }) => {
    const [rosterWeeks, setRosterWeeks] = useState([]);
    const [fantasyTeams, setFantasyTeams] = useState([]);
    const [selectedTeam, setSelectedTeam] = useState(null);

    useEffect(() => {
        const fetchRosterWeeks = async () => {
            try {
                // Fetch roster weeks
                const response = await api.get(`/leagues/${leagueId}/rosterWeeks`);
                setRosterWeeks(response.data); // Ensure it returns an array

                // Fetch fantasy teams
                const teamsResponse = await api.get(`/leagues/${leagueId}/fantasyTeams`);
                setFantasyTeams(teamsResponse.data);

                // Set the default selected team to "All Teams"
                setSelectedTeam(0); // 0 for "All Teams"
            } catch (error) {
                console.error('Error fetching data:', error);
            }
        };

        fetchRosterWeeks();
    }, [leagueId]);

    // Update the selected team when dropdown changes
    const handleTeamChange = (e) => {
        setSelectedTeam(parseInt(e.target.value));
    };

    // Render the table of teams and events for a specific selected team
const renderTable = () => {
    if (selectedTeam === 0) {
        return <div>Select a specific team to see their events.</div>; // Handle "All Teams" selection
    }

    // Find the selected roster based on fantasy_team_id
    const selectedRoster = rosterWeeks.find(team => team.fantasy_team_id === selectedTeam);

    // Check if selectedRoster exists and has roster data
    if (!selectedRoster || !selectedRoster.roster || selectedRoster.roster.length === 0) {
        return <div>Loading...</div>; // Update this message if there's no roster
    }

    return (
        <Table bordered hover>
            <thead>
                <tr className='table-secondary'>
                    <th>Team #</th>
                    {[...Array(5)].map((_, i) => (
                        <th key={i}>Week {i + 1}</th>
                    ))}
                </tr>
            </thead>
            <tbody>
                {selectedRoster.roster.map((team) => {
                    // Initialize an array to hold the event keys for each week
                    const weeklyEvents = Array(5).fill('-'); // Default to '-'

                    // Populate the weeklyEvents array with event keys if available
                    team.events.forEach(event => {
                        if (event.week >= 1 && event.week <= 5) {
                            weeklyEvents[event.week - 1] = event.event_key; // Set the event key in the correct week column
                        }
                    });

                    return (
                        <tr key={team.team_key}>
                            <td>{team.team_key}</td>
                            {weeklyEvents.map((eventKey, index) => (
                                <td key={index}>{eventKey}</td>
                            ))}
                        </tr>
                    );
                })}
            </tbody>
        </Table>
    );
};

    return (
        <div>
            <div className='row'>
                <div className="col md-2" />
                <div className='col md-8'>

            <Form.Group controlId="fantasyTeamSelect">
                <Form.Control
                    as="select"
                    value={selectedTeam || 0} // Ensure the value is non-null, default to 0 for "All Teams"
                    onChange={handleTeamChange}
                    className='text-center'
                    >
                    {/* "All Teams" option */}
                    <option value={0}>All Teams</option>
                    {fantasyTeams.map((team) => (
                        <option key={team.fantasy_team_id} value={team.fantasy_team_id}>
                            {team.team_name}
                        </option>
                    ))}
                </Form.Control>
            </Form.Group>
                    </div>
                    <div className='col md-2'/>
            </div>

            {/* Conditionally render Rosters or the selected team's table */}
            {selectedTeam === 0 ? (
                <Rosters leagueId={leagueId} /> // Render the Rosters component when "All Teams" is selected
            ) : (
                renderTable() // Render the specific team's roster table
            )}
        </div>
    );
};

export default RosterWeeks;
