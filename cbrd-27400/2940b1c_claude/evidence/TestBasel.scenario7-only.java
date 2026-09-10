import common.TestDbInfo;
import java.sql.*;
import java.io.*;
import java.lang.*;
import java.math.BigDecimal;
import java.util.*;


class scn_create extends Scenario/*{{{*/
{
  static int record_num = 100;

  protected void test_case () throws SQLException
  {
    try {
      execute ("drop table t1");
      commit();
    }
    catch (Exception e) {
      // skip
    }
    execute ("create table t1(a int primary key, b int, c int)");
    execute ("create index i_t1_b on t1(b)");
//    execute ("create reverse index on t1(a)");

    PreparedStatement stmt = con.prepareStatement ("insert into t1 values(?, ?, 0);");
    for (int i = 0; i < scn_create.record_num; i++)
	{
		stmt.setInt(1, i);
		if (i%2 == 0) {
			stmt.setInt(2, i-1);
		}
		else {
			stmt.setInt(2, i+1);
		}
		stmt.executeUpdate();
	}

    stmt.close ();
    System.out.println ("create done");
  }
}
/*}}}*/

class scn_select_by_pk extends Scenario/*{{{*/
{
  protected void test_case () throws SQLException
  {
    PreparedStatement stmt = con.prepareStatement ("select * from t1 where a = ?");
    Random rand = new Random (System.currentTimeMillis ());

    for (int i = 0;; i++)
	{
		float lap = static_timer_lap("");
		if (lap*1000 > TestBasel.test_time) break;

		stmt.setInt(1, rand.nextInt(scn_create.record_num));

		try {
			stmt.executeQuery();
		} catch (SQLException e) {
			TestBasel.inc_count();
			continue;
		}
	}

    stmt.close ();
  }
}
/*}}}*/

class scn_update_by_pk extends Scenario/*{{{*/
{
  protected void test_case () throws SQLException
  {
    PreparedStatement stmt = con.prepareStatement 
			("update t1 set c = 1 where a = ? using index pk_t1_a");
    Random rand = new Random (System.currentTimeMillis ());

    for (int i = 0;; i++)
	{
		float lap = static_timer_lap("");
		if (lap*1000 > TestBasel.test_time) break;

		stmt.setInt(1, rand.nextInt(scn_create.record_num));

		try {
			stmt.executeUpdate();
		} catch (SQLException e) {
			TestBasel.inc_count();
			//continue;
			break;
		}
	}

    stmt.close ();
  }
}
/*}}}*/

class scn_update_by_idx extends Scenario/*{{{*/
{
  protected void test_case () throws SQLException
  {
    PreparedStatement stmt = con.prepareStatement 
				("update t1 set c = 1 where b = ? using index i_t1_b");
    Random rand = new Random (System.currentTimeMillis ());

    for (int i = 0;; i++)
	{
		float lap = static_timer_lap("");
		if (lap*1000 > TestBasel.test_time) break;

		stmt.setInt(1, rand.nextInt(scn_create.record_num));

		try {
			stmt.executeUpdate();
		} catch (SQLException e) {
			TestBasel.inc_count();
			//continue;
			break;
		}
	}

    stmt.close ();
  }
}
/*}}}*/

class scn_select_by_idx extends Scenario/*{{{*/
{
  protected void test_case () throws SQLException
  {
    PreparedStatement stmt = con.prepareStatement ("select * from t1 where b = ?");
    Random rand = new Random (System.currentTimeMillis ());

    for (int i = 0;; i++)
	{
		float lap = static_timer_lap("");
		if (lap*1000 > TestBasel.test_time) break;

		stmt.setInt(1, rand.nextInt(scn_create.record_num));

		try {
			stmt.executeQuery();
		} catch (SQLException e) {
			TestBasel.inc_count();
			continue;
		}
	}

    stmt.close ();
  }
}
/*}}}*/

class scn_inc extends Scenario/*{{{*/
{
  protected void test_case () throws SQLException
  {
    PreparedStatement stmt = con.prepareStatement ("update t1 set c = 10 where a = ? using index pk_t1_a");
    for (int i = 0; ; i++)
      {
	float lap = static_timer_lap("");
	if (lap*1000 > TestBasel.test_time) break;

        stmt.setInt (1, i % scn_create.record_num);

	try {
		stmt.executeUpdate();
	} catch (SQLException e) {
		TestBasel.inc_count();
		continue;
	}
      }

    stmt.close ();
  }
}
/*}}}*/

class scn_dec extends Scenario/*{{{*/
{
  protected void test_case () throws SQLException
  {
    PreparedStatement stmt = con.prepareStatement ("update t1 set c = 10 where a = ? using index ri_t1_a");
    for (int i = 0; ; i++)
      {
	float lap = static_timer_lap("");
	if (lap*1000 > TestBasel.test_time) break;

        stmt.setInt (1, i % scn_create.record_num);

	try {
		stmt.executeUpdate();
	} catch (SQLException e) {
		TestBasel.inc_count();
		continue;
	}
      }

    stmt.close ();
  }
}
/*}}}*/

class scn_insert extends Scenario/*{{{*/
{
  protected void test_case () throws SQLException
  {
    set_autocommit(false);
    Random rand = new Random (System.currentTimeMillis ());
    PreparedStatement stmt = con.prepareStatement ("insert into t1 values(?, ?, 0)");
    PreparedStatement stmt_d = con.prepareStatement ("delete from t1 where a = ?");
    for (int i = 0; ; i++)
      {
        try
        {
	    float lap = static_timer_lap("");
	    if (lap*1000 > TestBasel.test_time) break;

	    int v1 = rand.nextInt(scn_create.record_num);
	    int v2 = rand.nextInt(scn_create.record_num);
            stmt.setInt (1, v1);
            stmt.setInt (2, v2);
            stmt.executeUpdate ();

            stmt_d.setInt (1, v1);
            stmt_d.executeUpdate ();
	    commit();
        }
        catch (SQLException e)
        {
	    con.rollback();
	    //e.printStackTrace();
	    TestBasel.inc_count();
	    continue;
        }
      }
    stmt.close ();
    stmt_d.close();
  }
}
/*}}}*/

class scn_select extends Scenario/*{{{*/
{
  protected void test_case () throws SQLException
  {
    PreparedStatement stmt = con.prepareStatement ("select * from t1 where b>0");
    for (int i = 0; ; i++)
      {
        try
        {
	    float lap = static_timer_lap("");
	    if (lap*1000 > TestBasel.test_time) break;

            stmt.executeQuery ();
        }
        catch (SQLException e)
        {
	    //e.printStackTrace();
	    TestBasel.inc_count();
	    continue;
        }
      }
    stmt.close ();
  }
}
/*}}}*/

class scn_update_pk extends Scenario/*{{{*/
{
  protected void test_case () throws SQLException
  {
    PreparedStatement stmt = con.prepareStatement 
			("update t1 set a = (a+1000)%2000 where a = ? using index pk_t1_a");
    Random rand = new Random (System.currentTimeMillis ());

    for (int i = 0;; i++)
	{
		float lap = static_timer_lap("");
		if (lap*1000 > TestBasel.test_time) break;

		try {
			int idx = rand.nextInt(scn_create.record_num);
			stmt.setInt(1, idx);
			stmt.executeUpdate();
			stmt.setInt(1, idx+1000);
			stmt.executeUpdate();
		} catch (SQLException e) {
			TestBasel.inc_count();
			continue;
		}
	}

    stmt.close ();
  }
}
/*}}}*/

class scn_update_idx extends Scenario/*{{{*/
{
  protected void test_case () throws SQLException
  {
    PreparedStatement stmt = con.prepareStatement 
			("update t1 set b = (b+1000)%2000 where b = ? using index i_t1_b");
    Random rand = new Random (System.currentTimeMillis ());

    for (int i = 0;; i++)
	{
		float lap = static_timer_lap("");
		if (lap*1000 > TestBasel.test_time) break;

		try {
			int idx = rand.nextInt(scn_create.record_num);
			stmt.setInt(1, idx);
			stmt.executeUpdate();
			stmt.setInt(1, idx+1000);
			stmt.executeUpdate();
		} catch (SQLException e) {
			TestBasel.inc_count();
			continue;
		}
	}

    stmt.close ();
  }
}
/*}}}*/

class scn_update_multi extends Scenario/*{{{*/
{
  protected void test_case () throws SQLException
  {
    PreparedStatement stmt = con.prepareStatement 
	("update t1 set b=(b+1000)%10000, c=(c+1000)%10000, d=(d+1000)%10000, e=(e+1000)%10000 where a=?");

    for (int i = 0;; i++)
	{
		try {
			float lap = static_timer_lap("");
			if (lap*1000 > TestBasel.test_time) break;

			ResultSet rs = execute("select * from t1 order by random()");

			int key;
			if (rs.next())
				key = rs.getInt(1);
			else	continue;

			stmt.setInt(1, key);
			stmt.executeUpdate();
		} catch (SQLException e) {
			//e.printStackTrace();
			TestBasel.inc_count();
			continue;
		}
	}

    stmt.close ();
  }
}
/*}}}*/

class scn_create_2 extends Scenario/*{{{*/
{
  static int record_num = 100;

  public int rec_num()
  {
	return scn_create_2.record_num;
  }

  protected void test_case () throws SQLException
  {
    try {
      execute ("drop table t1");
      commit();
    }
    catch (Exception e) {
      // skip
    }

    execute ("create table t1(a int primary key, b int, c int, d int, e int)");
    execute ("create index i_t1_b on t1(b)");
    execute ("create index i_t1_c on t1(c)");
    execute ("create index i_t1_d on t1(d)");
    execute ("create index i_t1_e on t1(e)");
    execute ("create reverse index ri_t1_a on t1(a)");
    execute ("create reverse index ri_t1_b on t1(b)");
    execute ("create reverse index ri_t1_c on t1(c)");
    execute ("create reverse index ri_t1_d on t1(d)");
    execute ("create reverse index ri_t1_e on t1(e)");

    PreparedStatement stmt = 
	con.prepareStatement ("insert into t1 values(?, ?, ?, ?, ?);");

    Random rand = new Random (System.currentTimeMillis ());
    for (int i = 0; i < rec_num(); i++)
	{
		stmt.setInt(1, i);
		stmt.setInt(2, rand.nextInt(scn_create.record_num));
		stmt.setInt(3, rand.nextInt(scn_create.record_num));
		stmt.setInt(4, rand.nextInt(scn_create.record_num));
		stmt.setInt(5, rand.nextInt(scn_create.record_num));

		stmt.executeUpdate();
	}

    stmt.close ();
    System.out.println ("create done");
  }
}
/*}}}*/



public class TestBasel
{
  static String url = ""; //init delay
  static int test_time = 1000 * 20;
  static int deadlock_count = 0;

  public synchronized static void inc_count()
  {
	TestBasel.deadlock_count++;
  }

  public static void run_test(Scenario[] s1, String init_query) throws SQLException/*{{{*/
  {
	for (int i=0; i<s1.length; i++) {
		s1[i].create_connection(TestBasel.url, "dba", "");
		if (init_query != "") {
			s1[i].execute(init_query);
		}
	}

	Scenario.static_timer_set();
	for (int i=0; i<s1.length; i++) {
		s1[i].do_test_thread();
	}

	for (int i=0; i<s1.length; i++) {
		s1[i].join();
		s1[i].close_connection();
	}

	System.out.println("## Deadlock count:" + deadlock_count + " in " + test_time + " millisec");
  }
/*}}}*/

  public static void run_test(Scenario[] s1, Scenario[] s2, String init_query) throws SQLException/*{{{*/
  {
	for (int i=0; i<s1.length; i++) {
		s1[i].create_connection(TestBasel.url, "dba", "");
		s2[i].create_connection(TestBasel.url, "dba", "");
		if (init_query != "") {
			s1[i].execute(init_query);
			s2[i].execute(init_query);
		}
	}

	Scenario.static_timer_set();
	for (int i=0; i<s1.length; i++) {
		s1[i].do_test_thread();
		s2[i].do_test_thread();
	}

	for (int i=0; i<s1.length; i++) {
		s1[i].join();
		s1[i].close_connection();
		s2[i].join();
		s2[i].close_connection();
	}

	System.out.println("## Deadlock count:" + deadlock_count + " in " + test_time + " millisec");
  }
/*}}}*/

  public static void main (String args[])/*{{{*/
  {
    try
    {
      Class.forName ("cubrid.jdbc.driver.CUBRIDDriver");


                TestDbInfo testDbInfo = TestDbInfo.call("shell_config.xml");
                testDbInfo.user = "dba";
                testDbInfo.password = "";
                testDbInfo.charset = "UTF-8";
                testDbInfo.dbname = "db_4633";
                TestBasel.url = "jdbc:cubrid:" + testDbInfo.ip
                                        + ":" + testDbInfo.port + ":" + testDbInfo.dbname + ":::"
                                        + "?charset=" + testDbInfo.charset;

	int size = 40;

	// allocation
	scn_update_by_pk u_p[] = new scn_update_by_pk[size];/*{{{*/
	scn_update_by_idx u_i[] = new scn_update_by_idx[size];
	scn_update_pk u_pk[] = new scn_update_pk[size];
	scn_update_idx u_ik[] = new scn_update_idx[size];
	scn_select_by_idx s_i[] = new scn_select_by_idx[size];
	scn_select_by_pk s_p[] = new scn_select_by_pk[size];
	scn_inc inc[] = new scn_inc[size];
	scn_dec dec[] = new scn_dec[size];
	scn_insert insert[] = new scn_insert[size];
	scn_select select[] = new scn_select[size];

	scn_update_multi u_m_nac[] = new scn_update_multi[size];

	for (int i=0; i<size; i++) {
		u_p[i] = new scn_update_by_pk();
		u_i[i] = new scn_update_by_idx();
		s_i[i] = new scn_select_by_idx();
		s_p[i] = new scn_select_by_pk();
		inc[i] = new scn_inc();
		dec[i] = new scn_dec();
		insert[i] = new scn_insert();
		select[i] = new scn_select();

		u_pk[i] = new scn_update_pk();
		u_ik[i] = new scn_update_idx();

		u_m_nac[i] = new scn_update_multi();
	}/*}}}*/

	// create db
	scn_create cr = new scn_create();/*{{{*/
	cr.create_connection (TestBasel.url, "dba", "");
	cr.do_test();
	cr.close_connection();/*}}}*/


	String tran_level = "";

	if (args.length > 0) 
		tran_level = "set transaction isolation level " + args[0];

	System.out.println("## Isolation level: " + tran_level);
	
	int no = 1;

	if (false) {
		System.out.println("## Scenario " + no++ + ": update by pk and index");
		TestBasel.deadlock_count = 0;
		TestBasel.run_test(u_p, u_i, tran_level);
	}

	if (false) {
		System.out.println("## Scenario " + no++ + ": update by pk and select by index");
		TestBasel.deadlock_count = 0;
		TestBasel.run_test(u_p, s_i, tran_level);
	}

	if (false) {
		System.out.println("## Scenario " + no++ + ": inc & dec update");
		TestBasel.deadlock_count = 0;
		TestBasel.run_test(inc, dec, tran_level);
	}

	if (false) {
		System.out.println("## Scenario " + no++ + ": update pk and select by index");
		TestBasel.deadlock_count = 0;
		TestBasel.run_test(u_pk, s_i, tran_level);
	}

	if (false) {
		System.out.println("## Scenario " + no++ + ": update pk and update idx");
		TestBasel.deadlock_count = 0;
		TestBasel.run_test(u_pk, u_ik, tran_level);
	}

	if (false) {
		System.out.println("## Scenario " + no++ + ": insert, delete & select");
		TestBasel.deadlock_count = 0;
		scn_create.record_num = 10000;
		TestBasel.run_test(insert, select, tran_level);
	}


	if (false) {
		System.out.println("## Scenario " + no++ + ": insert, delete & update idx");
		TestBasel.deadlock_count = 0;
		scn_create.record_num = 10000;
		TestBasel.run_test(insert, u_ik, tran_level);
	}


	scn_create_2 cr2 = new scn_create_2();/*{{{*/
	cr2.create_connection (TestBasel.url, "dba", "");
	cr2.do_test();
	cr2.close_connection();/*}}}*/

	if (true) {
		System.out.println("## Scenario " + no++ + ": update multi index in not ac");
		TestBasel.deadlock_count = 0;
		TestBasel.run_test(u_m_nac, tran_level);
	}

    } catch (Exception e)
    {
      e.printStackTrace ();
    }
  }
/*}}}*/
}


