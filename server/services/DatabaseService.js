// Simple database service stub
class DatabaseService {
  constructor() {
    this.agents = [];
    this.tasks = [];
    this.activities = [];
  }

  getAgents() {
    return this.agents;
  }

  getTasks() {
    return this.tasks;
  }

  getActivities() {
    return this.activities;
  }

  addTask(task) {
    this.tasks.push(task);
    return task;
  }

  addActivity(activity) {
    this.activities.push(activity);
    return activity;
  }
}

module.exports = new DatabaseService();