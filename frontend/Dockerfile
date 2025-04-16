FROM node:18-alpine

# Install yarn
RUN apk add --no-cache yarn

WORKDIR /app

# Copy package files
COPY package.json yarn.lock  ./

# Install dependencies using yarn
RUN yarn install --frozen-lockfile

COPY . .

# Build using yarn
RUN yarn build

FROM nginx:alpine
COPY --from=0 /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]