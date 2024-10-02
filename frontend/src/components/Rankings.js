// src/components/Rankings.js
import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import api from '../api';

const Rankings = () => {
  const {leagueId} = useParams();
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
  const maxWeeks = Math.max(...rankings.map(r => r.weekly_scores.length));
  
  return (
    <div className="container mt-5">
      <h1 className="mb-4">League Rankings</h1>
      <table className="table table-striped">
        <thead>
          <tr>
            <th scope="col">Rank</th>
            <th scope="col">Team Name</th>
            {Array.from({ length: maxWeeks }, (_, i) => (
              <th key={i} scope="col">Week {i + 1}</th>
            ))}
            <th scope="col">Total Ranking Points</th>
            <th scope="col">Tiebreaker</th>
          </tr>
        </thead>
        <tbody>
          {rankings.map((ranking, index) => (
            <tr key={ranking.fantasy_team_id}>
              <th scope="row">{index + 1}</th>
              <td>{ranking.fantasy_team_name}</td>
              {Array.from({ length: maxWeeks }, (_, weekIndex) => {
                const weekScore = ranking.weekly_scores[weekIndex];
                return (
                  <td key={weekIndex}>
                    {weekScore ? `${weekScore.ranking_points} (${weekScore.weekly_score})` : 'N/A'}
                  </td>
                );
              })}
              <td>{ranking.total_ranking_points}</td>
              <td>{ranking.tiebreaker}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default Rankings;
