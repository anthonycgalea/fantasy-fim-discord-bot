// src/components/LeagueDrafts.js
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api'; // Adjust this path based on your project structure

const LeagueDrafts = ({ leagueId }) => {
  const [drafts, setDrafts] = useState([]);

  useEffect(() => {
    const fetchDrafts = async () => {
      try {
        const response = await api.get(`/leagues/${leagueId}/drafts`); // Adjust the endpoint if necessary
        console.log(response.data); // Log the response for debugging
        setDrafts(response.data);
      } catch (error) {
        console.error('Error fetching drafts:', error);
      }
    };

    fetchDrafts();
  }, [leagueId]);

  return (
    <div className="container mt-5">
      <table className="table table-bordered">
        <thead className="thead-light table-secondary">
          <tr>
            <th></th>
            <th>Event Key</th>
            <th>Rounds</th>
          </tr>
        </thead>
        <tbody>
          {drafts.map((draft) => (
            <tr key={draft.draft_id}>
              <td>
                <Link to={`/drafts/${draft.draft_id}`}>Draft {draft.draft_id}</Link>
              </td>
              <td>{draft.event_key}</td>
              <td>{draft.rounds}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default LeagueDrafts;
