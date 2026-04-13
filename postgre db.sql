--
-- PostgreSQL database dump
--

\restrict shdKX75CixfdwEaz5hEvU6rALSfuZbOUkue3UfcGDUmfgBTtqi2sQftgECKAhZM

-- Dumped from database version 17.6
-- Dumped by pg_dump version 17.6

-- Started on 2026-04-13 19:33:52

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 221 (class 1259 OID 16632)
-- Name: admins; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.admins (
    admin_id integer NOT NULL,
    firstname character varying(50) NOT NULL,
    lastname character varying(50) NOT NULL,
    password_hash character varying(255) NOT NULL,
    email character varying(100) NOT NULL
);


ALTER TABLE public.admins OWNER TO postgres;

--
-- TOC entry 220 (class 1259 OID 16631)
-- Name: admins_admin_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.admins_admin_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.admins_admin_id_seq OWNER TO postgres;

--
-- TOC entry 4963 (class 0 OID 0)
-- Dependencies: 220
-- Name: admins_admin_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.admins_admin_id_seq OWNED BY public.admins.admin_id;


--
-- TOC entry 225 (class 1259 OID 16667)
-- Name: chat_messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_messages (
    message_id uuid DEFAULT gen_random_uuid() NOT NULL,
    session_id uuid NOT NULL,
    role character varying(20) NOT NULL,
    content text NOT NULL,
    sources_json jsonb,
    model_mode character varying(20),
    grounded boolean,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chat_messages_role_check CHECK (((role)::text = ANY ((ARRAY['user'::character varying, 'assistant'::character varying, 'system'::character varying])::text[])))
);


ALTER TABLE public.chat_messages OWNER TO postgres;

--
-- TOC entry 224 (class 1259 OID 16652)
-- Name: chat_sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_sessions (
    session_id uuid DEFAULT gen_random_uuid() NOT NULL,
    employee_id integer NOT NULL,
    title character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    last_message_at timestamp with time zone DEFAULT now() NOT NULL,
    is_archived boolean DEFAULT false NOT NULL,
    deleted_at timestamp with time zone
);


ALTER TABLE public.chat_sessions OWNER TO postgres;

--
-- TOC entry 217 (class 1259 OID 16609)
-- Name: documents; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.documents (
    document_id uuid NOT NULL,
    file_name character varying(255) NOT NULL,
    file_path character varying(500) NOT NULL,
    status character varying(20) DEFAULT 'uploaded'::character varying NOT NULL,
    total_chunks integer DEFAULT 0 NOT NULL,
    uploaded_time timestamp with time zone DEFAULT now() NOT NULL,
    indexed_time timestamp with time zone,
    error_message text
);


ALTER TABLE public.documents OWNER TO postgres;

--
-- TOC entry 219 (class 1259 OID 16620)
-- Name: employees; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.employees (
    emp_id integer NOT NULL,
    firstname character varying(50) NOT NULL,
    lastname character varying(50) NOT NULL,
    email character varying(100) NOT NULL,
    password_hash character varying(255) NOT NULL,
    status character varying(20) DEFAULT 'disabled'::character varying NOT NULL,
    department character varying(50),
    designation character varying(50)
);


ALTER TABLE public.employees OWNER TO postgres;

--
-- TOC entry 218 (class 1259 OID 16619)
-- Name: employees_emp_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.employees_emp_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.employees_emp_id_seq OWNER TO postgres;

--
-- TOC entry 4964 (class 0 OID 0)
-- Dependencies: 218
-- Name: employees_emp_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.employees_emp_id_seq OWNED BY public.employees.emp_id;


--
-- TOC entry 223 (class 1259 OID 16643)
-- Name: system_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.system_logs (
    log_id integer NOT NULL,
    actor_type character varying(20) NOT NULL,
    actor_id integer NOT NULL,
    action_type character varying(50) NOT NULL,
    action_description text,
    affected_table character varying(50),
    "timestamp" timestamp with time zone DEFAULT now() NOT NULL,
    ip_address inet,
    status character varying(20)
);


ALTER TABLE public.system_logs OWNER TO postgres;

--
-- TOC entry 222 (class 1259 OID 16642)
-- Name: system_logs_log_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.system_logs_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.system_logs_log_id_seq OWNER TO postgres;

--
-- TOC entry 4965 (class 0 OID 0)
-- Dependencies: 222
-- Name: system_logs_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.system_logs_log_id_seq OWNED BY public.system_logs.log_id;


--
-- TOC entry 4769 (class 2604 OID 16635)
-- Name: admins admin_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admins ALTER COLUMN admin_id SET DEFAULT nextval('public.admins_admin_id_seq'::regclass);


--
-- TOC entry 4767 (class 2604 OID 16623)
-- Name: employees emp_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employees ALTER COLUMN emp_id SET DEFAULT nextval('public.employees_emp_id_seq'::regclass);


--
-- TOC entry 4770 (class 2604 OID 16646)
-- Name: system_logs log_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.system_logs ALTER COLUMN log_id SET DEFAULT nextval('public.system_logs_log_id_seq'::regclass);


--
-- TOC entry 4953 (class 0 OID 16632)
-- Dependencies: 221
-- Data for Name: admins; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.admins (admin_id, firstname, lastname, password_hash, email) FROM stdin;
2	Admin	User	$2b$12$6DaR0cYtRvmBPL7CEnOOTeRXzu.vRSvGAiFLsg38u0PKpEkHtskSW	admin@company.com
\.


--
-- TOC entry 4957 (class 0 OID 16667)
-- Dependencies: 225
-- Data for Name: chat_messages; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.chat_messages (message_id, session_id, role, content, sources_json, model_mode, grounded, created_at) FROM stdin;
\.


--
-- TOC entry 4956 (class 0 OID 16652)
-- Dependencies: 224
-- Data for Name: chat_sessions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.chat_sessions (session_id, employee_id, title, created_at, updated_at, last_message_at, is_archived, deleted_at) FROM stdin;
\.


--
-- TOC entry 4949 (class 0 OID 16609)
-- Dependencies: 217
-- Data for Name: documents; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.documents (document_id, file_name, file_path, status, total_chunks, uploaded_time, indexed_time, error_message) FROM stdin;
\.


--
-- TOC entry 4951 (class 0 OID 16620)
-- Dependencies: 219
-- Data for Name: employees; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.employees (emp_id, firstname, lastname, email, password_hash, status, department, designation) FROM stdin;
\.


--
-- TOC entry 4955 (class 0 OID 16643)
-- Dependencies: 223
-- Data for Name: system_logs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.system_logs (log_id, actor_type, actor_id, action_type, action_description, affected_table, "timestamp", ip_address, status) FROM stdin;
\.


--
-- TOC entry 4966 (class 0 OID 0)
-- Dependencies: 220
-- Name: admins_admin_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.admins_admin_id_seq', 2, true);


--
-- TOC entry 4967 (class 0 OID 0)
-- Dependencies: 218
-- Name: employees_emp_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.employees_emp_id_seq', 10, true);


--
-- TOC entry 4968 (class 0 OID 0)
-- Dependencies: 222
-- Name: system_logs_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.system_logs_log_id_seq', 125, true);


--
-- TOC entry 4787 (class 2606 OID 16641)
-- Name: admins admins_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admins
    ADD CONSTRAINT admins_email_key UNIQUE (email);


--
-- TOC entry 4789 (class 2606 OID 16639)
-- Name: admins admins_firstname_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admins
    ADD CONSTRAINT admins_firstname_key UNIQUE (firstname);


--
-- TOC entry 4791 (class 2606 OID 16637)
-- Name: admins admins_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admins
    ADD CONSTRAINT admins_pkey PRIMARY KEY (admin_id);


--
-- TOC entry 4799 (class 2606 OID 16676)
-- Name: chat_messages chat_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_pkey PRIMARY KEY (message_id);


--
-- TOC entry 4795 (class 2606 OID 16661)
-- Name: chat_sessions chat_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_sessions
    ADD CONSTRAINT chat_sessions_pkey PRIMARY KEY (session_id);


--
-- TOC entry 4781 (class 2606 OID 16618)
-- Name: documents documents_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (document_id);


--
-- TOC entry 4783 (class 2606 OID 16630)
-- Name: employees employees_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employees
    ADD CONSTRAINT employees_email_key UNIQUE (email);


--
-- TOC entry 4785 (class 2606 OID 16628)
-- Name: employees employees_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employees
    ADD CONSTRAINT employees_pkey PRIMARY KEY (emp_id);


--
-- TOC entry 4793 (class 2606 OID 16651)
-- Name: system_logs system_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.system_logs
    ADD CONSTRAINT system_logs_pkey PRIMARY KEY (log_id);


--
-- TOC entry 4800 (class 1259 OID 16685)
-- Name: idx_chat_messages_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_messages_created_at ON public.chat_messages USING btree (created_at);


--
-- TOC entry 4801 (class 1259 OID 16684)
-- Name: idx_chat_messages_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_messages_session_id ON public.chat_messages USING btree (session_id);


--
-- TOC entry 4796 (class 1259 OID 16682)
-- Name: idx_chat_sessions_employee_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_sessions_employee_id ON public.chat_sessions USING btree (employee_id);


--
-- TOC entry 4797 (class 1259 OID 16683)
-- Name: idx_chat_sessions_last_message_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_sessions_last_message_at ON public.chat_sessions USING btree (last_message_at DESC);


--
-- TOC entry 4803 (class 2606 OID 16677)
-- Name: chat_messages fk_chat_messages_session; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT fk_chat_messages_session FOREIGN KEY (session_id) REFERENCES public.chat_sessions(session_id) ON DELETE CASCADE;


--
-- TOC entry 4802 (class 2606 OID 16662)
-- Name: chat_sessions fk_chat_sessions_employee; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_sessions
    ADD CONSTRAINT fk_chat_sessions_employee FOREIGN KEY (employee_id) REFERENCES public.employees(emp_id) ON DELETE CASCADE;


-- Completed on 2026-04-13 19:33:53

--
-- PostgreSQL database dump complete
--

\unrestrict shdKX75CixfdwEaz5hEvU6rALSfuZbOUkue3UfcGDUmfgBTtqi2sQftgECKAhZM

