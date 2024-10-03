// src/components/Rankings.js
import React, { useEffect, useState } from 'react';
import api from '../api';

const Rankings = ({ leagueId }) => {
  const [rankings, setRankings] = useState([]);

  useEffect(() => {
    const fetchRankings = async () => {
      try {
        const response = await api.get(`/leagues/${leagueId}/rankings`); // Update league ID as needed
        setRankings(response.data);
      } catch (error) {
        console.error('Error fetching rankings:', error);
      }
    };

    fetchRankings();
  }, [leagueId]);

  // Determine the maximum number of weeks for dynamic columns
  //const maxWeeks = Math.max(...rankings.map(r => r.weekly_scores.length));
  
  return (
    <table className="table table-hover">
      <thead className='table-secondary'>
        <tr>
          <th scope="col">Rank</th>
          <th scope="col">Team Name</th>
          <th scope="col">Total Ranking Points</th>
          <th scope="col">Tiebreaker</th>
        </tr>
      </thead>
      <tbody>
        {rankings.map((ranking, index) => (
          <tr key={ranking.fantasy_team_id}>
            <th scope="row">{index + 1}</th>
            <td>{ranking.fantasy_team_name}</td>
            <td>{ranking.total_ranking_points}</td>
            <td>{ranking.tiebreaker}</td>
          </tr>
        ))}
      </tbody>
    </table>
    
  );
};

export default Rankings;
