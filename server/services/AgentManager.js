// Agent management service stub
class AgentManager {
  constructor() {
    this.agents = new Map();
  }

  registerAgent(agent) {
    this.agents.set(agent.id, agent);
    return agent;
  }

  getAgent(id) {
    return this.agents.get(id);
  }

  getAllAgents() {
    return Array.from(this.agents.values());
  }

  updateAgent(id, updates) {
    const agent = this.agents.get(id);
    if (agent) {
      Object.assign(agent, updates);
    }
    return agent;
  }
}

module.exports = new AgentManager();