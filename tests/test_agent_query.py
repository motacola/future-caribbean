from agent.query import ask, explain_lead, routes_for_persona, what_changed


def sample_desk():
    return {
        "cycle_id": "20260527",
        "cluster_count": 1,
        "dispatch_count": 2,
        "boost_lines": ["Guyana enhanced investment upranked +5"],
        "clusters": [
            {
                "title": "Guyana: capital surge",
                "country_cluster": "Guyana",
                "decision": "Which market to investigate",
                "evidence": "WB FDI surge detected: Guyana",
                "evidence_grade": "A - multi-source",
                "confidence_score": 100,
                "freshness": "sustained",
                "feedback_summary": "Feedback this cycle: 1 forwarded.",
                "personas": [
                    {
                        "persona": "Diaspora Investor",
                        "channel": "Email brief + Telegram",
                        "action": "Investigate Guyana as a capital deployment target.",
                        "dispatch_id": "DSP-1",
                        "feedback_status": "forwarded",
                    },
                    {
                        "persona": "Regional Founder/Operator",
                        "channel": "Telegram",
                        "action": "Assess competitive positioning in Guyana.",
                        "dispatch_id": "DSP-2",
                        "feedback_status": "ignored",
                    },
                ],
            }
        ],
    }


def test_explain_lead_includes_decision_and_citation():
    answer = explain_lead(sample_desk())
    assert "Guyana: capital surge" in answer
    assert "Which market to investigate" in answer
    assert "Sources:" in answer


def test_investor_query_returns_investor_route():
    answer = routes_for_persona(sample_desk(), "investor")
    assert "Investigate Guyana" in answer
    assert "DSP-1" in answer


def test_what_changed_includes_boosts():
    answer = what_changed(sample_desk())
    assert "Guyana enhanced investment upranked +5" in answer


def test_ask_routes_lead_question():
    answer = ask("why is Guyana first", sample_desk())
    assert "Lead signal" in answer
