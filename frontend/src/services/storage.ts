import { Preferences } from '@capacitor/preferences';

export interface item {
  id: number,
  title: string,
  value: string,
  modified: number
}

export async function set(key: string, value: any): Promise<void> {
  await Preferences.set({
    key: key,
    value: JSON.stringify(value)
  });
}

export async function get(key: string): Promise<any> {
  const item: string | any = await Preferences.get({ key: key });
  return JSON.parse(item.value);
}

export async function remove(key: string): Promise<void> {
  await Preferences.remove({
    key: key
  });
}

export async function update(key: string, value: any): Promise<any> {
  const item: string | any = await Preferences.get({ key: key });
  let dataarray: any[] = JSON.parse(item.value);
  if (dataarray == null) {

    let dataarray: any[] = [];
    dataarray.push(value);
    await Preferences.remove({
      key: key
    });
    await Preferences.set({
      key: key,
      value: JSON.stringify(dataarray)
    });
    return dataarray;

  } else {

    dataarray.push(value);
    await Preferences.remove({
      key: key
    });
    await Preferences.set({
      key: key,
      value: JSON.stringify(dataarray)
    });
    return dataarray;
  }

}