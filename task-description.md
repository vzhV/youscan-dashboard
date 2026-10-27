# YouScan Full-Stack Engineer Test Task – Dashboard with parsed data

This task reflects the type of work you may encounter in the role.

Build a full-stack dashboard application with a React frontend and a backend using one of the supported stacks below.

You may use any tools that help you work productively, including libraries, packages, UI frameworks, and AI tools.

We will assess your solution’s **architecture**, **code style**, **complexity**, and **quality of decomposition**.

## Functional Requirements

### Dashboard layout

Display widgets in a grid with three widgets per row and an unlimited number of rows.

Support five widget types: line chart, bar chart, stacked bar chart, pie chart, and text.

### Initial dashboard and provided data

You will receive two files alongside this task. Throughout the description, these are referred to as the provided data.

| File format | Used for                 |
| ----------- | ------------------------ |
| .xlsx       | Line chart and pie chart |
| .csv        | Stacked bar chart        |

The dashboard must initially contain a line chart, a pie chart, and a stacked bar chart, populated with the corresponding provided data.

Parse the files programmatically and store the resulting data for use by the dashboard. The parsing mechanism must be included in the repository and support importing additional files – not just the two supplied examples.

You may use existing libraries or packages to parse the files. Writing a parser from scratch is not required; the goal is to build a reusable mechanism for importing data into storage.

    Important!
    Hardcoding the provided data instead of parsing the files will result in the submission being rejected.

### Widget creation and management

Users must be able to add any supported widget type to the grid using a "Create widget" button.

The initial chart widgets must use the provided data. Newly created chart widgets must use randomized data.

Text widgets must support an Edit → Save flow.

Saved changes must update the backend and persist after a page reload.

All widgets must be deletable. Each widget must display its own loading and error states when applicable.

## Technical Requirements

### Backend

Use one of the following stacks:

    Node.js 20+ with TypeScript

OR

    .NET Core

OR

    Python with any framework

Validate incoming data and return appropriate HTTP status codes for errors.

### Frontend

Use the latest version of React with TypeScript.

Fetch widget data from the backend and render the corresponding charts or text.

Additional tooling and UI libraries, such as Vite or Ant Design, are allowed.

Recharts or Chart.js is recommended for charts, but any charting library is acceptable.

## Acceptance Criteria

### The submission must meet all requirements above.

Before submitting, verify that:

- The application is deployed and accessible for testing, using Vercel or another platform of your choice.

- The initial dashboard displays the required charts using data parsed from the provided files.

- The reusable file-parsing mechanism is included in the repository, and the provided data is not hardcoded.

- Users can create and delete widgets, and newly created charts use randomized data.

- Text edits are saved to the backend and persist after a page reload.

- Loading and error states are shown per widget, and errors are handled gracefully.

- TypeScript type checking passes without errors.
