// src/types/scoreTypes.ts

// Define a type for individual subject scores
export interface Subject {
  examMode: string;
  score: number;
  attempted: number;
  total: number;
  timeSpent: number;
  year: string;
}

// Define a type for overall scores per subject category, e.g., "Math", "Science", etc.
export interface SubjectScores {
  [subjectName: string]: Subject;
}

// Define the main type that represents each student's or test record's subject score
export interface SubjectScore {
  examType: string;
  subjects: SubjectScores; // Each subject with its score and time spent
  date: string; // Optional: Date or other metadata related to the score record
}

export interface Streak {
  start_date: string;
  noOfDays: number;
  last_updated: string;
}

export interface StreakInfo {
  currentStreak: Streak;
  bestStreak: Streak;
}
