import React, { useEffect, useState } from 'react';
import api from '../api'; // Adjust the import path based on your project structure
import './Rosters.css'; // Import the CSS file for styles

const Rosters = ({ leagueId }) => {
  const [rosters, setRosters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchRosters = async () => {
      try {
        const response = await api.get(`/leagues/${leagueId}/rosters`);
        setRosters(response.data);
        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    };

    fetchRosters();
  }, [leagueId]);

  if (loading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div>Error: {error}</div>;
  }

  // Find the maximum roster length to create rows
  const maxRosterLength = Math.max(...rosters.map((team) => team.roster.length));
  
  // Collect the team members in a transposed format
  const transposedRoster = Array.from({ length: maxRosterLength }, (_, memberIndex) =>
    rosters.map(team => (team.roster[memberIndex] ? team.roster[memberIndex] : ''))
  );

  return (
    <div className="table-responsive mt-4">
      <table className="table table-bordered">
        <thead className='table-secondary'>
          <tr>
            {rosters.map(({ fantasy_team_name }) => (
              <th className="equal-width" key={fantasy_team_name}>{fantasy_team_name}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {transposedRoster.map((memberIds, index) => (
            <tr key={index}>
              {memberIds.map((memberId, teamIndex) => (
                <td key={teamIndex}>{memberId}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default Rosters;
