# Frontend Dockerfile
FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy application code
COPY . .

# Build Next.js application (for production)
# RUN npm run build

# Expose port
EXPOSE 3000

# Development command
CMD ["npm", "run", "dev"]

# Production command
# CMD ["npm", "start"]