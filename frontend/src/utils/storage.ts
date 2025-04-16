import { Preferences } from '@capacitor/preferences';

export interface Item {
  id: number;
  title: string;
  value: string;
  modified: number;
}

export async function set(key: string, value: any): Promise<void> {
  await Preferences.set({
    key: key,
    value: JSON.stringify(value)
  });
}

export async function get(key: string): Promise<any> {
  const item = await Preferences.get({ key: key });
  return item.value ? JSON.parse(item.value) : null;
}

export async function remove(key: string): Promise<void> {
  await Preferences.remove({ key: key });
}

export async function update(key: string, value: any): Promise<any> {
  const item = await Preferences.get({ key: key });
  let dataArray: any[] = item.value ? JSON.parse(item.value) : [];
  
  dataArray.push(value);
  
  await Preferences.set({
    key: key,
    value: JSON.stringify(dataArray)
  });

  return dataArray;
}
