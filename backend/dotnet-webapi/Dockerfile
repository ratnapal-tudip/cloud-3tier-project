FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY ["Cloud3Tier.Api.csproj", "./"]
RUN dotnet restore "Cloud3Tier.Api.csproj"
COPY . .
RUN dotnet build "Cloud3Tier.Api.csproj" -c Release -o /app/build
RUN dotnet publish "Cloud3Tier.Api.csproj" -c Release -o /app/publish

FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS final
WORKDIR /app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY --from=build /app/publish .
EXPOSE 5000
ENTRYPOINT ["dotnet", "Cloud3Tier.Api.dll", "--urls", "http://0.0.0.0:5000"]
