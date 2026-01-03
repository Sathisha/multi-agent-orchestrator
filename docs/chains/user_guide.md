# Chain Builder User Guide

The Chain Builder is a visual orchestration tool that allows you to create complex multi-agent workflows.

## Getting Started

1.  **Accessing the Builder**: Navigate to the **Chains** section in the side activity bar.
2.  **Creating a Chain**: Click the **Create Workflow** button. A new canvas will open with initial `START` and `END` nodes.

## Building Your Workflow

### Adding Agents
- Open the agent palette by clicking the **+** (Add Agent) button in the toolbar.
- Select the agent you want to add to the chain.
- The agent node will appear on the canvas.

### Connecting Nodes
- Click and drag from the output port (bottom) of any node to the input port (top) of another node.
- Workflows must always start from the `START` node and eventually reach the `END` node.

### Configuring Nodes
- Click on any agent node to open the **Node Configuration** panel on the right.
- **Label**: Give the node a descriptive name.
- **Agent**: Select or change the specific agent used for this step.
- **Execution Config**: Set timeouts and retry policies.
- **Apply**: Update the canvas without closing the panel.

## Executing & Monitoring

- **Execute**: Click the **Execute** tab in the top bar to run your chain.
- **History**: View past executions and their step-by-step logs in the **History** tab.
- **Visualization**: While running, active nodes will pulse, and completed nodes will show a checkmark.
