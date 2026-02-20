"""Tests for the LinkedIn direct CSV parser."""

import csv
import io
import zipfile
from pathlib import Path

import pytest

from futureproof.gatherers.linkedin import (
    LinkedInGatherer,
    _parse_certifications,
    _parse_company_follows,
    _parse_connections,
    _parse_education,
    _parse_endorsements,
    _parse_inferences,
    _parse_job_applications,
    _parse_job_preferences,
    _parse_languages,
    _parse_learning,
    _parse_messages,
    _parse_positions,
    _parse_profile,
    _parse_projects,
    _parse_recommendations_given,
    _parse_recommendations_received,
    _parse_shares,
    _parse_skills,
    _read_csv,
    _read_csv_variants,
)


def _make_zip(files: dict[str, list[dict[str, str]]]) -> io.BytesIO:
    """Create an in-memory ZIP with CSV files."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, rows in files.items():
            if not rows:
                zf.writestr(name, "")
                continue
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
            zf.writestr(name, output.getvalue())
    buf.seek(0)
    return buf


def _make_zip_file(tmp_path: Path, files: dict[str, list[dict[str, str]]]) -> Path:
    """Create a ZIP file on disk for the gatherer."""
    zip_path = tmp_path / "linkedin_export.zip"
    buf = _make_zip(files)
    zip_path.write_bytes(buf.getvalue())
    return zip_path


# =============================================================================
# Tier 1 — Core Career Data
# =============================================================================


class TestTier1Profile:
    def test_parse_profile(self):
        rows = [
            {
                "First Name": "John",
                "Last Name": "Doe",
                "Headline": "Senior Engineer",
                "Summary": "Experienced developer.",
                "Industry": "Technology",
                "Geo Location": "Madrid, Spain",
            }
        ]
        result = _parse_profile(rows)
        assert "# John Doe" in result
        assert "Senior Engineer" in result
        assert "Experienced developer." in result
        assert "Technology" in result
        assert "Madrid, Spain" in result

    def test_parse_profile_empty(self):
        assert _parse_profile([]) == ""


class TestTier1Positions:
    def test_parse_positions(self):
        rows = [
            {
                "Company Name": "Acme Corp",
                "Title": "Lead Engineer",
                "Location": "Remote",
                "Started On": "Jan 2020",
                "Finished On": "Dec 2023",
                "Description": "Led a team of 5.",
            }
        ]
        result = _parse_positions(rows)
        assert "## Experience" in result
        assert "### Acme Corp" in result
        assert "**Lead Engineer**" in result
        assert "Jan 2020 – Dec 2023" in result
        assert "Led a team of 5." in result

    def test_current_position(self):
        rows = [
            {
                "Company Name": "Current Co",
                "Title": "CTO",
                "Location": "",
                "Started On": "Jan 2024",
                "Finished On": "",
                "Description": "",
            }
        ]
        result = _parse_positions(rows)
        assert "Jan 2024 – Present" in result


class TestTier1Education:
    def test_parse_education(self):
        rows = [
            {
                "School Name": "MIT",
                "Degree Name": "M.S.",
                "Field Of Study": "Computer Science",
                "Start Date": "2015",
                "End Date": "2017",
                "Notes": "",
                "Activities and Societies": "Hackathon club",
            }
        ]
        result = _parse_education(rows)
        assert "### MIT" in result
        assert "**M.S.**" in result
        assert "Computer Science" in result
        assert "Hackathon club" in result


class TestTier1Skills:
    def test_parse_skills(self):
        rows = [{"Name": "Python"}, {"Name": "Rust"}, {"Name": "Go"}]
        result = _parse_skills(rows)
        assert "## Skills" in result
        assert "Python, Rust, Go" in result

    def test_empty_skills(self):
        assert _parse_skills([]) == ""


class TestTier1Certifications:
    def test_parse_certifications(self):
        rows = [
            {
                "Name": "AWS Solutions Architect",
                "Authority": "Amazon",
                "Started On": "2023",
                "Url": "https://example.com/cert",
            }
        ]
        result = _parse_certifications(rows)
        assert "AWS Solutions Architect" in result
        assert "(Amazon)" in result
        assert "[link]" in result


class TestTier1Others:
    def test_parse_languages(self):
        rows = [
            {"Name": "English", "Proficiency": "Native"},
            {"Name": "Spanish", "Proficiency": "Professional"},
        ]
        result = _parse_languages(rows)
        assert "English: Native" in result
        assert "Spanish: Professional" in result

    def test_parse_projects(self):
        rows = [
            {
                "Title": "Open Source Tool",
                "Description": "A CLI tool.",
                "Url": "https://github.com/example",
                "Started On": "2022",
            }
        ]
        result = _parse_projects(rows)
        assert "### Open Source Tool" in result
        assert "A CLI tool." in result

    def test_parse_recommendations_received(self):
        rows = [
            {
                "First Name": "Jane",
                "Last Name": "Smith",
                "Company": "BigCo",
                "Text": "Great engineer!",
            }
        ]
        result = _parse_recommendations_received(rows)
        assert '"Great engineer!"' in result
        assert "Jane Smith" in result
        assert "BigCo" in result

    def test_parse_endorsements(self):
        rows = [
            {
                "Skill Name": "Python",
                "Endorser First Name": "Alice",
                "Endorser Last Name": "Bob",
            }
        ]
        result = _parse_endorsements(rows)
        assert "Python: endorsed by Alice Bob" in result

    def test_parse_recommendations_given(self):
        rows = [
            {
                "First Name": "Bob",
                "Last Name": "Jones",
                "Company": "StartupX",
                "Text": "Wonderful colleague.",
            }
        ]
        result = _parse_recommendations_given(rows)
        assert '"Wonderful colleague."' in result


# =============================================================================
# Tier 2 — Career Intelligence
# =============================================================================


class TestTier2:
    def test_parse_learning(self):
        rows = [
            {
                "Title": "Deep Learning Specialization",
                "Content Type": "COURSE",
                "Completed Date": "2023-06-15",
            }
        ]
        result = _parse_learning(rows)
        assert "Deep Learning Specialization" in result
        assert "(COURSE)" in result
        assert "2023-06-15" in result

    def test_parse_job_applications(self):
        rows = [
            {
                "Application Date": "2023-01-15",
                "Job Title": "Staff Engineer",
                "Company Name": "Google",
            }
        ]
        result = _parse_job_applications(rows)
        assert "**Staff Engineer**" in result
        assert "Google" in result

    def test_parse_job_preferences(self):
        rows = [{"Job Type": "Full-time", "Location": "Remote", "Title": "Engineer"}]
        result = _parse_job_preferences(rows)
        assert "Job Type: Full-time" in result
        assert "Location: Remote" in result

    def test_parse_shares(self):
        rows = [
            {
                "Date": "2023-05-01",
                "Commentary": "Excited to announce...",
                "ShareLink": "https://linkedin.com/post/1",
            }
        ]
        result = _parse_shares(rows)
        assert "Excited to announce..." in result
        assert "### 2023-05-01" in result

    def test_parse_shares_skips_empty(self):
        rows = [{"Date": "2023-05-01", "Commentary": "", "ShareLink": ""}]
        result = _parse_shares(rows)
        # Should skip entries with no commentary
        assert "### 2023-05-01" not in result

    def test_parse_inferences(self):
        rows = [{"Type": "Career", "Inference": "Software Engineering"}]
        result = _parse_inferences(rows)
        assert "Career: Software Engineering" in result


# =============================================================================
# Tier 2 — Connections & Messages
# =============================================================================


class TestConnections:
    def test_parse_connections_individual_records(self):
        rows = [
            {
                "First Name": "María",
                "Last Name": "García",
                "Email Address": "maria@accenture.com",
                "Company": "Accenture",
                "Position": "Senior Developer",
                "Connected On": "15 Jan 2023",
                "URL": "https://linkedin.com/in/mariagarcia",
            },
            {
                "First Name": "John",
                "Last Name": "Smith",
                "Email Address": "",
                "Company": "Google",
                "Position": "SWE",
                "Connected On": "3 Mar 2022",
                "URL": "",
            },
        ]
        result = _parse_connections(rows)
        assert "## Connections" in result
        assert "**María García**" in result
        assert "Company: Accenture" in result
        assert "Position: Senior Developer" in result
        assert "Connected: 15 Jan 2023" in result
        assert "Email: maria@accenture.com" in result
        assert "URL: https://linkedin.com/in/mariagarcia" in result
        assert "**John Smith**" in result
        assert "Company: Google" in result

    def test_parse_connections_summary_included(self):
        rows = [
            {"First Name": "A", "Last Name": "B", "Company": "Google", "Position": "SWE"},
            {"First Name": "C", "Last Name": "D", "Company": "Google", "Position": "PM"},
            {"First Name": "E", "Last Name": "F", "Company": "Meta", "Position": "SWE"},
        ]
        result = _parse_connections(rows)
        assert "Network Summary" in result
        assert "3 connections" in result
        assert "Google (2)" in result

    def test_parse_connections_compact_format(self):
        """Each connection is a single pipe-separated line, no ### headers."""
        rows = [
            {
                "First Name": "Alice",
                "Last Name": "Wong",
                "Company": "Accenture",
                "Position": "Manager",
            },
        ]
        result = _parse_connections(rows)
        assert "###" not in result.split("## Connections")[1]
        assert "**Alice Wong** | Company: Accenture | Position: Manager" in result

    def test_parse_connections_partial_fields(self):
        rows = [
            {"First Name": "Alice", "Last Name": "Wong", "Company": "Accenture", "Position": ""},
        ]
        result = _parse_connections(rows)
        assert "**Alice Wong**" in result
        assert "Company: Accenture" in result
        # No Position field when empty
        assert "Position:" not in result.split("Alice Wong")[1]

    def test_parse_connections_skips_nameless(self):
        rows = [
            {"First Name": "", "Last Name": "", "Company": "Unknown", "Position": "Role"},
        ]
        result = _parse_connections(rows)
        # No individual connection entry — only summary
        assert "Company: Unknown" not in result
        assert "Position: Role" not in result
        # Summary should still count
        assert "1 connections" in result

    def test_parse_connections_empty(self):
        assert _parse_connections([]) == ""


class TestMessages:
    def test_parse_messages_grouped(self):
        rows = [
            {
                "CONVERSATION ID": "conv1",
                "CONVERSATION TITLE": "María García",
                "FROM": "María García",
                "SENDER PROFILE URL": "https://linkedin.com/in/maria",
                "DATE": "2024-03-15 10:00:00",
                "SUBJECT": "",
                "CONTENT": "Hi, I saw your profile!",
            },
            {
                "CONVERSATION ID": "conv1",
                "CONVERSATION TITLE": "María García",
                "FROM": "You",
                "SENDER PROFILE URL": "",
                "DATE": "2024-03-16 09:00:00",
                "SUBJECT": "",
                "CONTENT": "Thanks for reaching out!",
            },
        ]
        result = _parse_messages(rows)
        assert "## Messages" in result
        assert "### Conversation: María García" in result
        assert "**María García**: Hi, I saw your profile!" in result
        assert "**You**: Thanks for reaching out!" in result
        assert "_2024-03-15 10:00:00_" in result

    def test_parse_messages_multiple_conversations(self):
        rows = [
            {
                "CONVERSATION ID": "conv1",
                "CONVERSATION TITLE": "Alice",
                "FROM": "Alice",
                "DATE": "2024-01-01",
                "CONTENT": "Hello",
            },
            {
                "CONVERSATION ID": "conv2",
                "CONVERSATION TITLE": "Bob",
                "FROM": "Bob",
                "DATE": "2024-02-01",
                "CONTENT": "Hey there",
            },
        ]
        result = _parse_messages(rows)
        assert "### Conversation: Alice" in result
        assert "### Conversation: Bob" in result

    def test_parse_messages_with_subject(self):
        rows = [
            {
                "CONVERSATION ID": "conv1",
                "CONVERSATION TITLE": "Recruiter",
                "FROM": "Recruiter",
                "DATE": "2024-01-01",
                "SUBJECT": "Job Opportunity at Accenture Spain",
                "CONTENT": "We have an opening...",
            },
        ]
        result = _parse_messages(rows)
        assert "**Subject: Job Opportunity at Accenture Spain**" in result

    def test_parse_messages_skips_empty_content(self):
        rows = [
            {
                "CONVERSATION ID": "conv1",
                "CONVERSATION TITLE": "Test",
                "FROM": "Someone",
                "DATE": "2024-01-01",
                "CONTENT": "",
            },
        ]
        result = _parse_messages(rows)
        assert "**Someone**" not in result

    def test_parse_messages_strips_html(self):
        rows = [
            {
                "CONVERSATION ID": "conv1",
                "CONVERSATION TITLE": "Recruiter",
                "FROM": "Recruiter",
                "DATE": "2024-01-01",
                "CONTENT": '<p class="spinmail">Hi Juan,</p><p><strong>Great profile!</strong></p>',
            },
        ]
        result = _parse_messages(rows)
        assert "<p" not in result
        assert "<strong>" not in result
        assert "Hi Juan," in result
        assert "Great profile!" in result

    def test_parse_messages_empty(self):
        assert _parse_messages([]) == ""


# =============================================================================
# Tier 3 — Network Summary
# =============================================================================


class TestTier3:
    def test_parse_company_follows(self):
        rows = [{"Organization": "Google"}, {"Organization": "Meta"}]
        result = _parse_company_follows(rows)
        assert "Following 2 companies" in result


# =============================================================================
# ZIP helpers
# =============================================================================


class TestZipHelpers:
    def test_read_csv_from_zip(self):
        buf = _make_zip({"Skills.csv": [{"Name": "Python"}, {"Name": "Go"}]})
        with zipfile.ZipFile(buf) as zf:
            rows = _read_csv(zf, "Skills.csv")
        assert len(rows) == 2
        assert rows[0]["Name"] == "Python"

    def test_read_csv_missing(self):
        buf = _make_zip({})
        with zipfile.ZipFile(buf) as zf:
            rows = _read_csv(zf, "Nonexistent.csv")
        assert rows == []

    def test_read_csv_variants(self):
        files = {
            "Jobs/Job Applications.csv": [
                {"Job Title": "Eng1", "Company Name": "A", "Application Date": "2023"}
            ],
            "Jobs/Job Applications_1.csv": [
                {"Job Title": "Eng2", "Company Name": "B", "Application Date": "2024"}
            ],
        }
        buf = _make_zip(files)
        with zipfile.ZipFile(buf) as zf:
            rows = _read_csv_variants(zf, "Jobs/Job Applications.csv")
        assert len(rows) == 2
        titles = {r["Job Title"] for r in rows}
        assert titles == {"Eng1", "Eng2"}


# =============================================================================
# Integration — full gatherer
# =============================================================================


class TestLinkedInGatherer:
    def test_gather_full(self, tmp_path):
        files = {
            "Profile.csv": [
                {
                    "First Name": "Jane",
                    "Last Name": "Doe",
                    "Headline": "Data Scientist",
                    "Summary": "ML expert.",
                    "Industry": "AI",
                    "Geo Location": "London",
                }
            ],
            "Positions.csv": [
                {
                    "Company Name": "DeepMind",
                    "Title": "Research Scientist",
                    "Location": "London",
                    "Started On": "2020",
                    "Finished On": "",
                    "Description": "Working on AGI.",
                }
            ],
            "Skills.csv": [{"Name": "PyTorch"}, {"Name": "TensorFlow"}],
            "Connections.csv": [
                {
                    "First Name": "Alice",
                    "Last Name": "Lee",
                    "Email Address": "alice@google.com",
                    "Company": "Google",
                    "Position": "SWE",
                    "Connected On": "1 Jan 2023",
                    "URL": "https://linkedin.com/in/alicelee",
                },
                {
                    "First Name": "Bob",
                    "Last Name": "Chen",
                    "Email Address": "",
                    "Company": "Google",
                    "Position": "SWE",
                    "Connected On": "2 Feb 2023",
                    "URL": "",
                },
            ],
        }
        zip_path = _make_zip_file(tmp_path, files)
        gatherer = LinkedInGatherer()
        result = gatherer.gather(zip_path)

        assert isinstance(result, str)
        assert "# Jane Doe" in result
        assert "### DeepMind" in result
        assert "PyTorch, TensorFlow" in result
        assert "**Alice Lee**" in result
        assert "**Bob Chen**" in result
        assert "2 connections" in result

    def test_gather_missing_zip(self, tmp_path):
        gatherer = LinkedInGatherer()
        with pytest.raises(FileNotFoundError):
            gatherer.gather(tmp_path / "nonexistent.zip")

    def test_gather_empty_zip(self, tmp_path):
        zip_path = _make_zip_file(tmp_path, {})
        gatherer = LinkedInGatherer()
        result = gatherer.gather(zip_path)
        assert result == ""
