"""Edit this file to change the resume. The UI reads everything from here."""

RESUME = {
    "name": "Alex Morgan",
    "title": "Full-stack developer",
    "location": "Perth, Australia",
    "contact": [
        {"label": "Email", "value": "alex@example.com", "href": "mailto:alex@example.com"},
        {"label": "GitHub", "value": "github.com/alexmorgan", "href": "https://github.com/alexmorgan"},
        {"label": "Web", "value": "alexmorgan.dev", "href": "https://alexmorgan.dev"},
    ],
    "summary": (
        "I build fast, readable web software and care about the details users "
        "actually touch: forms, tables, and the moments between clicks."
    ),
    "experience": [
        {
            "role": "Senior developer",
            "org": "Northlight Systems",
            "period": "2022 – Present",
            "points": [
                "Led a rebuild of the customer dashboard, cutting load time from 4.1s to 1.2s.",
                "Introduced a shared component library used by five product teams.",
            ],
            "skills": ["Python", "Flask", "PostgreSQL", "JavaScript"],
        },
        {
            "role": "Developer",
            "org": "Bluegum Digital",
            "period": "2019 – 2022",
            "points": [
                "Shipped 30+ client sites and internal tools on a small team.",
                "Automated deployments, reducing release time from an hour to ten minutes.",
            ],
            "skills": ["JavaScript", "PHP", "MySQL", "CSS"],
        },
    ],
    "projects": [
        {
            "name": "Tidewatch",
            "blurb": "Tide and swell tracker with an offline-first mobile view.",
            "skills": ["Python", "Flask", "CSS"],
        },
        {
            "name": "Ledgerlite",
            "blurb": "Plain-language bookkeeping for sole traders.",
            "skills": ["JavaScript", "PostgreSQL"],
        },
    ],
    "education": [
        {"title": "B.Sc. Computer Science", "org": "University of Western Australia", "period": "2016 – 2019"},
    ],
}
