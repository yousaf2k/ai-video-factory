/**
 * Home page - redirects to projects
 */
import { redirect } from 'next/navigation';

export default function Home() {
  redirect('/projects');
}
