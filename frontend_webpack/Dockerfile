# Dockerfile

# Step 1: Use an official Node.js runtime as a parent image
FROM node:18-alpine

# Step 2: Set the working directory in the container
WORKDIR /app

# Step 3: Copy package.json and package-lock.json into the container
COPY package*.json /app/

# Step 4: Install Node.js dependencies
RUN npm install --legacy-peer-deps

# Step 5: Copy the current directory contents into the container at /app
COPY . /app/

# Step 6: Build the React app
RUN npm run build

# Step 7: Expose port 3000 for React development server
EXPOSE 3000

# Step 8: Start the React app
CMD ["npm", "start"]
