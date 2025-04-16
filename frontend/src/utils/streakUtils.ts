import { StreakInfo } from '../interfaces/score';

// Helper function to check if two dates are consecutive
const areDatesConsecutive = (
  lastDate: string,
  currentDate: string
): boolean => {
  const last = new Date(lastDate);
  const current = new Date(currentDate);
  const diffInTime = current.getTime() - last.getTime();
  const diffInDays = diffInTime / (1000 * 3600 * 24);
  return diffInDays === 1;
};

// Function to calculate study streak
export const calculateStudyStreak = (
  streaks: StreakInfo,
  today: string
): StreakInfo => {
  const { currentStreak, bestStreak } = streaks;

  if (areDatesConsecutive(currentStreak.last_updated, today)) {
    // Continue the streak
    currentStreak.noOfDays += 1;
    currentStreak.last_updated = today;

    // Update best streak if current streak is the longest
    if (currentStreak.noOfDays > bestStreak.noOfDays) {
      bestStreak.start_date = currentStreak.start_date;
      bestStreak.noOfDays = currentStreak.noOfDays;
      bestStreak.last_updated = today;
    }
  } else if (currentStreak.last_updated !== today) {
    // Missed a day, reset the current streak
    streaks.currentStreak = {
      start_date: today,
      noOfDays: 1,
      last_updated: today,
    };
  }

  return streaks;
};

// Function to format streak display with a flame icon
export const formatStreakDisplay = (streakDays: number): string => {
  return `${streakDays} 🔥`;
};
