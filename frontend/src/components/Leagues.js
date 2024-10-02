// src/components/Leagues.js
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api'; // Adjust this path based on your project structure

const Leagues = () => {
  const [leagues, setLeagues] = useState([]);

  useEffect(() => {
    const fetchLeagues = async () => {
      try {
        const response = await api.get('/leagues'); // Adjust the endpoint if necessary
        console.log(response.data); // Log the response for debugging
        setLeagues(response.data);
      } catch (error) {
        console.error('Error fetching leagues:', error);
      }
    };

    fetchLeagues();
  }, []);

  return (
    <div className="container mt-5">
      <h1 className="mb-4 text-center">Active Leagues</h1>
      <table className="table table-bordered">
        <thead className="thead-light">
          <tr>
            <th>League Name</th>
            <th>Rankings</th>
            <th>Drafts</th>
          </tr>
        </thead>
        <tbody>
          {leagues.map((league) => (
            <tr key={league.league_id}>
              <td>{league.league_name}</td>
              <td>
                <Link className="btn btn-primary" to={`/leagues/${league.league_id}/rankings`}>
                  Rankings
                </Link>
                </td>
                <td>
                <Link className="btn btn-info" to={`/leagues/${league.league_id}/drafts`}>
                    Drafts
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default Leagues;
