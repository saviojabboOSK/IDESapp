# Frontend Dockerfile for IDES 2.0 React application with Node.js build and optimized production serving
FROM node:18-alpine as build

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY pnpm-lock.yaml* ./

# Install pnpm and dependencies
RUN npm install -g pnpm && pnpm install --frozen-lockfile

# Copy source code
COPY . .

# Build application
RUN pnpm build

# Production stage
FROM node:18-alpine as production

WORKDIR /app

# Install serve for production serving
RUN npm install -g serve pnpm

# Copy built application
COPY --from=build /app/dist ./dist
COPY package*.json ./

# Install only production dependencies
RUN pnpm install --prod --frozen-lockfile

# Expose port
EXPOSE 5173

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5173 || exit 1

# Serve the application
CMD ["serve", "-s", "dist", "-l", "5173"]
