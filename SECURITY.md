# Security and Privacy

Charlotte is local-first, but it is an agent system with potentially powerful access to files, messages, spreadsheets, web services, and tablets. Local-first describes where users keep their data; it does not remove the need to configure permissions carefully.

## Data boundary

The public repository contains reusable code, skills, examples, and the shipped public-domain pedagogy pack. It should not contain:

- student or family records;
- real household configuration;
- purchased curricula or private pedagogy sources;
- Signal databases or attachments;
- spreadsheets, dashboards, generated slides, generated media, or backups;
- API keys, remote-control tokens, cookies, credentials, or private hosts; or
- prompts and logs containing identifying family information.

Charlotte ignores the normal local configuration and content roots, including `students.yaml`, `.env`, `runtime.yaml`, `image-generation.yaml`, curricula, spreadsheets, dashboards, generated slides and images, logs, attachments, and backups. Treat ignore rules as a safety net, not as authorization to place secrets in the working tree.

## Operator responsibilities

- Give the agent and its tools access only to the directories, services, and devices needed for the workflows you enable.
- Review `students.yaml`, runtime mounts, MCP configuration, scheduled jobs, and remote endpoints before use.
- Keep `.env`, MindFeast remote tokens, messaging credentials, and provider keys out of prompts, logs, commits, screenshots, and bug reports.
- Restrict local HTTP services and device-control endpoints to trusted networks and authenticated clients.
- Back up spreadsheets and other records before adopting automated writes.
- Review generated lesson or record content before relying on it. Charlotte can make identification, transcription, classification, and factual errors.
- Check the privacy and retention terms of every configured model provider, search service, messaging gateway, and runtime. Data sent to those services leaves the local boundary.
- Keep purchased or copyrighted source material in ignored local content roots and follow the terms that apply to it.

## Reporting a vulnerability

Do not open a public issue containing exploit details, credentials, private records, or identifying family information. Use GitHub's private vulnerability-reporting channel for this repository if it is available. If it is unavailable, contact the maintainer privately through the contact method on the maintainer's GitHub profile and include only the minimum information needed to establish contact.

Include the affected commit or version, impact, reproduction conditions, and a sanitized proof of concept. Remove all real family data and secrets. Because Charlotte is currently maintained without a formal security team or response-time guarantee, avoid disclosing details publicly until the maintainer has had a reasonable opportunity to investigate.

## Supported versions

Security fixes are made on the current default branch. No older release line is presently maintained.
