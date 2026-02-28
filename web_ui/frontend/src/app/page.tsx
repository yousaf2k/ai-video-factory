/**
 * Home page - redirects to sessions
 */
import { redirect } from 'next/navigation';

export default function Home() {
  redirect('/sessions');
}
