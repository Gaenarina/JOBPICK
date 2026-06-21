import { filterJobPostingsByPreferences } from "@/lib/matchingFilters";

const filteredJobPostings = filterJobPostingsByPreferences(
  jobPostings,
  resume.matchPreferences
);