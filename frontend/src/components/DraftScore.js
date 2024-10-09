// src/components/DraftScore.js
import React, { useEffect, useState } from 'react';
import { Table, Row, Col } from 'react-bootstrap';
import api from '../api'; // Adjust the import path based on your project structure

const DraftScore = ({ draftId }) => {
    const [leagueInfo, setLeagueInfo] = useState({});
    const [scores, setScores] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchDraftAndScores = async () => {
            try {
                // Fetch draft details to get league_id
                const draftResponse = await api.get(`/drafts/${draftId}`);

                // Fetch fantasy scores based on draftId
                const scoresResponse = await api.get(`/drafts/${draftId}/fantasyScores`);
                setScores(scoresResponse.data); // Ensure this returns an array

                // Fetch league info using league_id from the draft object
                const leagueResponse = await api.get(`/leagues/${draftResponse.data.league_id}`);
                setLeagueInfo(leagueResponse.data);
            } catch (error) {
                setError('Error fetching data');
                console.error('Error fetching data:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchDraftAndScores();
    }, [draftId]);

    if (loading) return <div>Loading scores...</div>;
    if (error) return <div>{error}</div>;

    const renderTeamTable = (fantasy_team) => {
        const weeklyStarts = leagueInfo.weekly_starts || 0; // Ensure this is defined
        const fantasyScore = scores.find(score => score.fantasy_team_id === fantasy_team.fantasy_team_id) || {};

        return (
            <Col xs={12} md={3} key={fantasy_team.fantasy_team_id} className="mb-3">
                <Table bordered hover>
                    <thead>
                        <tr>
                            <th colSpan={2} className="table-secondary">{fantasy_team.fantasy_team_name}</th>
                        </tr>
                        <tr>
                            <th className="table-secondary">Score</th>
                            <td>{fantasyScore.event_score || 0}</td>
                        </tr>
                        <tr>
                            <th className="table-secondary">RP</th>
                            <td>{fantasyScore.rank_points || 0}</td>
                        </tr>
                        <tr>
                            <th className="table-secondary">Team #</th>
                            <th className="table-secondary">Score</th>
                        </tr>
                    </thead>
                    <tbody>
                        {Array.from({ length: weeklyStarts }, (_, index) => {
                            const teamStarted = fantasy_team.teams[index] || { team_number: '' };
                            const matchingTeam = fantasyScore.teams.find(team => team.team_number === teamStarted.team_number) || { event_score: 0 };

                            return (
                                <tr key={index}>
                                    <td>{teamStarted.team_number || ''}</td>
                                    <td>{matchingTeam.event_score || 0}</td>
                                </tr>
                            );
                        })}
                    </tbody>
                </Table>
            </Col>
        );
    };

    return (
        <Row className="justify-content-center">
            {Array.isArray(scores) && scores.length > 0 ? (
                scores.map(fantasy_team => renderTeamTable(fantasy_team))
            ) : (
                <div>No scores available</div>
            )}
        </Row>
    );
};

export default DraftScore;
