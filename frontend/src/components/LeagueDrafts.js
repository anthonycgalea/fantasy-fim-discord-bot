// src/components/LeagueDrafts.js
import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import api from '../api'; // Adjust this path based on your project structure

const LeagueDrafts = () => {
  const { leagueId } = useParams(); // Get the leagueId from the URL
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
      <h1 className="mb-4">Drafts for League ID: {leagueId}</h1>
      <table className="table table-bordered">
        <thead className="thead-light">
          <tr>
            <th>Draft ID</th>
            <th>Event Key</th>
            <th>Rounds</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {drafts.map((draft) => (
            <tr key={draft.draft_id}>
              <td>
                <Link to={`/drafts/${draft.draft_id}`}>{draft.draft_id}</Link>
              </td>
              <td>{draft.event_key}</td>
              <td>{draft.rounds}</td>
              <td>
                <Link className="btn btn-primary" to={`/drafts/${draft.draft_id}`}>
                  View Draft
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default LeagueDrafts;
